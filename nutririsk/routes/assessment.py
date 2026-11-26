import io
import csv
import json
import logging
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    flash, abort, current_app, send_file
)

logger = logging.getLogger(__name__)
from nutririsk.db import get_db, insert_assessment, get_assessment_secure
from nutririsk.auth.utils import login_required
from nutririsk.ml.features import CHOICES, LABELS, validate_and_parse_input
from nutririsk.ml.prediction import predict_nutritional_risk, get_model_bundle
from nutririsk.ml.explainability import compute_shap_attributions, XAI_METHODOLOGY_INFO
from nutririsk.pdf_report import generate_assessment_pdf

assessment_bp = Blueprint("assessment", __name__)

@assessment_bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict_page():
    """Nutritional risk assessment submission form and processing."""
    if request.method == "POST":
        parsed_data, error_msg = validate_and_parse_input(request.form)
        if error_msg:
            flash(error_msg, "err")
            return render_template("predict.html", C=CHOICES, v=request.form)
            
        try:
            result_data = predict_nutritional_risk(parsed_data)
        except Exception as e:
            logger.error("Inference engine exception during assessment: %s", e, exc_info=True)
            if current_app.config.get("DEBUG"):
                flash(f"Inference error: {str(e)}", "err")
            else:
                flash("A processing error occurred while generating the assessment. The incident has been safely logged.", "err")
            return render_template("predict.html", C=CHOICES, v=request.form)
            
        subject = request.form.get("subject", "").strip() or "Self Assessment"
        db = get_db()
        model_ver = current_app.config.get("MODEL_VERSION", "v1.0-xgboost")
        aid = insert_assessment(
            db=db,
            user_id=session["uid"],
            subject=subject,
            inputs=parsed_data,
            risk=result_data["risk"],
            confidence=result_data["confidence"],
            probabilities=result_data["probabilities"],
            factors=result_data["factors"],
            bmi=result_data["bmi"],
            model_version=model_ver
        )
        return redirect(url_for("assessment.result", aid=aid))
        
    return render_template("predict.html", C=CHOICES, v={})

@assessment_bp.route("/result/<int:aid>")
@login_required
def result(aid):
    """Detailed risk stratification, class probabilities, and XAI factor attribution view."""
    db = get_db()
    is_admin = (session.get("role") == "admin")
    assessment = get_assessment_secure(db, aid, user_id=session["uid"], is_admin=is_admin)
    
    if not assessment:
        abort(404)
        
    inputs = json.loads(assessment["inputs"])
    height_m = float(inputs.get("height_cm", 170.0)) / 100.0
    weight_kg = float(inputs.get("weight_kg", 70.0))
    inputs["bmi"] = assessment["bmi"] if "bmi" in assessment.keys() and assessment["bmi"] else round(weight_kg / (height_m ** 2), 2)
    
    raw_probs = json.loads(assessment["probs"])
    if isinstance(raw_probs, dict):
        probabilities = [float(raw_probs.get(lbl, 0.0)) for lbl in LABELS]
    elif isinstance(raw_probs, list):
        probabilities = [float(p) for p in raw_probs]
    else:
        probabilities = [0.0, 0.0, 0.0]
    factors = json.loads(assessment["factors"])
    advice_text = current_app.config["ADVICE"].get(
        assessment["risk"],
        "Consult a clinical healthcare provider for personalized evaluation."
    )

    # Compute SHAP on the fly for the selected model
    shap_data = None
    try:
        bundle = get_model_bundle()
        predicted_idx = LABELS.index(assessment["risk"]) if assessment["risk"] in LABELS else 0
        shap_data = compute_shap_attributions(bundle["pipeline"], inputs, predicted_idx)
    except Exception as exc:
        current_app.logger.warning("Could not compute SHAP for result view: %s", exc)

    return render_template(
        "result.html",
        a=assessment,
        inp=inputs,
        probs=probabilities,
        factors=factors,
        labels=LABELS,
        advice=advice_text,
        shap=shap_data,
        xai_info=XAI_METHODOLOGY_INFO
    )

@assessment_bp.route("/result/<int:aid>/pdf")
@assessment_bp.route("/assessment/<int:aid>/download")
@login_required
def download_pdf(aid):
    """
    Generates and downloads publication-grade clinical assessment PDF report (Prompt 19).
    Enforces multi-tenant authorization: regular users can only download their own reports;
    administrators can download any system report.
    """
    db = get_db()
    is_admin = (session.get("role") == "admin")
    assessment = get_assessment_secure(db, aid, user_id=session["uid"], is_admin=is_admin)

    if not assessment:
        abort(404)

    inputs = json.loads(assessment["inputs"])
    height_m = float(inputs.get("height_cm", 170.0)) / 100.0
    weight_kg = float(inputs.get("weight_kg", 70.0))
    inputs["bmi"] = assessment["bmi"] if "bmi" in assessment.keys() and assessment["bmi"] else round(weight_kg / (height_m ** 2), 2)
    advice_text = current_app.config["ADVICE"].get(assessment["risk"], "")
    disclaimer_text = current_app.config.get("DISCLAIMER", "")

    # Query evaluator/clinician name (without exposing password hash)
    user_row = db.execute("SELECT name FROM users WHERE id = ?", (assessment["user_id"],)).fetchone()
    assessor_name = user_row["name"] if user_row else "Healthcare Clinician"

    # Query active model name
    from nutririsk.db import get_active_model_metadata
    active_meta = get_active_model_metadata(db)
    model_name = active_meta["model_name"] if active_meta and "model_name" in active_meta.keys() else "XGBoost Classifier"

    pdf_buffer = generate_assessment_pdf(
        assessment_record=dict(assessment),
        inputs_dict=inputs,
        advice_text=advice_text,
        disclaimer_text=disclaimer_text,
        assessor_name=assessor_name,
        model_name=model_name
    )

    filename = f"NutriRisk_Assessment_{aid}_{assessment['created'][:10]}.pdf"
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

import math

SORT_OPTIONS = {
    "date_desc": ("created DESC", "Date (Newest First)"),
    "date_asc": ("created ASC", "Date (Oldest First)"),
    "risk_desc": ("CASE risk WHEN 'High Risk' THEN 1 WHEN 'Moderate Risk' THEN 2 WHEN 'Low Risk' THEN 3 ELSE 4 END ASC, created DESC", "Risk (Highest First)"),
    "risk_asc": ("CASE risk WHEN 'Low Risk' THEN 1 WHEN 'Moderate Risk' THEN 2 WHEN 'High Risk' THEN 3 ELSE 4 END ASC, created DESC", "Risk (Lowest First)"),
    "confidence_desc": ("confidence DESC", "Confidence (Highest First)"),
    "confidence_asc": ("confidence ASC", "Confidence (Lowest First)"),
    "bmi_desc": ("bmi DESC", "BMI (Highest First)"),
    "bmi_asc": ("bmi ASC", "BMI (Lowest First)")
}

@assessment_bp.route("/history")
@login_required
def history():
    """
    Complete Prediction History module (Prompt 15).
    Provides searchable, filterable, sortable, and paginated assessment history
    with class probability inspection, Chart.js visualizations, and secure multi-tenant isolation.
    """
    db = get_db()
    uid = session["uid"]
    
    query = request.args.get("q", "").strip()
    selected_risk = request.args.get("risk", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    sort_key = request.args.get("sort", "date_desc").strip()
    if sort_key not in SORT_OPTIONS:
        sort_key = "date_desc"
        
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    per_page = request.args.get("per_page", 10, type=int)
    if per_page not in [5, 10, 20, 50]:
        per_page = 10
        
    # Build filter conditions
    where_clauses = ["user_id = ?"]
    params = [uid]
    
    if query:
        clean_q = query.lstrip("#").strip()
        if clean_q.isdigit():
            where_clauses.append("(id = ? OR subject LIKE ?)")
            params.extend([int(clean_q), f"%{query}%"])
        else:
            where_clauses.append("subject LIKE ?")
            params.append(f"%{query}%")
            
    if selected_risk in LABELS:
        where_clauses.append("risk = ?")
        params.append(selected_risk)
        
    if start_date:
        where_clauses.append("substr(created, 1, 10) >= ?")
        params.append(start_date)
        
    if end_date:
        where_clauses.append("substr(created, 1, 10) <= ?")
        params.append(end_date)
        
    where_sql = " AND ".join(where_clauses)
    
    # 1. Total matching count
    count_sql = f"SELECT COUNT(*) FROM assessments WHERE {where_sql}"
    total_records = db.execute(count_sql, params).fetchone()[0]
    
    # 2. Total pages & pagination bounds
    total_pages = max(1, math.ceil(total_records / per_page)) if total_records > 0 else 1
    if page > total_pages and total_records > 0:
        page = total_pages
    offset = (page - 1) * per_page
    
    # 3. Chart Aggregations across all matching filtered records
    dist_sql = f"SELECT risk, COUNT(*) as cnt FROM assessments WHERE {where_sql} GROUP BY risk"
    chart_risk_counts = {"Low Risk": 0, "Moderate Risk": 0, "High Risk": 0}
    for row in db.execute(dist_sql, params).fetchall():
        if row["risk"] in chart_risk_counts:
            chart_risk_counts[row["risk"]] = row["cnt"]
            
    timeline_sql = f"""SELECT substr(created, 1, 10) as dt, COUNT(*) as cnt 
                       FROM assessments 
                       WHERE {where_sql} 
                       GROUP BY dt 
                       ORDER BY dt ASC"""
    trend_rows = db.execute(timeline_sql, params).fetchall()
    chart_dates = [r["dt"] for r in trend_rows]
    chart_counts = [r["cnt"] for r in trend_rows]
    
    # 4. Paginated Data Query
    sort_sql = SORT_OPTIONS[sort_key][0]
    data_sql = f"""SELECT * FROM assessments 
                   WHERE {where_sql} 
                   ORDER BY {sort_sql} 
                   LIMIT ? OFFSET ?"""
    data_params = params + [per_page, offset]
    db_rows = db.execute(data_sql, data_params).fetchall()
    
    # 5. Enrich rows with parsed class probabilities
    enriched_rows = []
    for r in db_rows:
        item = dict(r)
        p_dict = {"Low Risk": 0.0, "Moderate Risk": 0.0, "High Risk": 0.0}
        try:
            raw_p = json.loads(r["probs"])
            if isinstance(raw_p, dict):
                for k, v in raw_p.items():
                    if k in p_dict:
                        p_dict[k] = float(v)
            elif isinstance(raw_p, (list, tuple)):
                for idx, lbl in enumerate(LABELS):
                    if idx < len(raw_p):
                        p_dict[lbl] = float(raw_p[idx])
        except Exception:
            pass
        item["probs_dict"] = p_dict
        enriched_rows.append(item)
        
    filter_args = {
        "q": query,
        "risk": selected_risk,
        "start_date": start_date,
        "end_date": end_date,
        "sort": sort_key,
        "per_page": per_page
    }
    
    start_record = offset + 1 if total_records > 0 else 0
    end_record = min(offset + per_page, total_records)
    
    return render_template(
        "history.html",
        rows=enriched_rows,
        total_records=total_records,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        start_record=start_record,
        end_record=end_record,
        filter_args=filter_args,
        sort_options=SORT_OPTIONS,
        q=query,
        r=selected_risk,
        start_date=start_date,
        end_date=end_date,
        sort=sort_key,
        labels=LABELS,
        chart_risk_counts=chart_risk_counts,
        chart_dates=chart_dates,
        chart_counts=chart_counts
    )


@assessment_bp.route("/batch/sample-template")
@login_required
def download_batch_template():
    """Generates and downloads a clean CSV template for batch patient screening."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "subject", "age", "sex", "height_cm", "weight_kg", "food_groups",
        "meals_per_day", "activity", "income", "education", "residence", "recent_illness"
    ])
    # 3 representative clinical example rows
    writer.writerow(["Patient Alpha (Underweight)", 68, "Female", 158.0, 39.0, 2, 2, "Low", "Low", "Primary", "Rural", "Yes"])
    writer.writerow(["Patient Beta (Moderate Risk)", 45, "Male", 170.0, 62.0, 4, 3, "Moderate", "Middle", "Secondary", "Urban", "No"])
    writer.writerow(["Patient Gamma (Healthy Reference)", 28, "Male", 178.0, 74.0, 7, 4, "High", "High", "Higher", "Urban", "No"])
    
    mem_stream = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(
        mem_stream,
        mimetype="text/csv",
        as_attachment=True,
        download_name="nutririsk_batch_template.csv"
    )


@assessment_bp.route("/batch", methods=["GET", "POST"])
@login_required
def batch_screening():
    """High-throughput multi-patient CSV ingestion and risk stratification."""
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Please select a valid CSV file to upload.", "err")
            return render_template("batch.html", batch_summary=None)
            
        if not file.filename.lower().endswith(".csv"):
            flash("Invalid file format. Please upload a comma-separated .csv file.", "err")
            return render_template("batch.html", batch_summary=None)
            
        try:
            content = file.stream.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
        except Exception as e:
            logger.error("Failed to decode uploaded CSV: %s", e)
            flash("Could not parse the CSV file. Please ensure it is saved in UTF-8 encoding.", "err")
            return render_template("batch.html", batch_summary=None)
            
        required_cols = {"age", "sex", "height_cm", "weight_kg", "food_groups", "meals_per_day", "activity", "income", "education", "residence", "recent_illness"}
        if not reader.fieldnames or not required_cols.issubset({c.strip().lower() for c in reader.fieldnames}):
            missing = required_cols - {c.strip().lower() for c in (reader.fieldnames or [])}
            flash(f"CSV header is missing required column(s): {', '.join(sorted(missing))}. Please use the sample template.", "err")
            return render_template("batch.html", batch_summary=None)
            
        db = get_db()
        model_ver = current_app.config.get("MODEL_VERSION", "v1.0-xgboost")
        user_id = session["uid"]
        
        results = []
        errors = []
        row_idx = 1
        
        low_count = 0
        moderate_count = 0
        high_count = 0
        
        for raw_row in reader:
            row_idx += 1
            # Normalize keys to lower-case stripped
            normalized_row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items() if k}
            subject = normalized_row.get("subject") or f"Batch Patient #{row_idx}"
            
            parsed_data, err_msg = validate_and_parse_input(normalized_row)
            if err_msg:
                errors.append({
                    "row": row_idx,
                    "subject": subject,
                    "reason": err_msg
                })
                continue
                
            try:
                pred = predict_nutritional_risk(parsed_data)
                aid = insert_assessment(
                    db=db,
                    user_id=user_id,
                    subject=subject,
                    inputs=parsed_data,
                    risk=pred["risk"],
                    confidence=pred["confidence"],
                    probabilities=pred["probabilities"],
                    factors=pred["factors"],
                    bmi=pred["bmi"],
                    model_version=model_ver
                )
                
                if pred["risk"] == "Low Risk":
                    low_count += 1
                elif pred["risk"] == "Moderate Risk":
                    moderate_count += 1
                else:
                    high_count += 1
                    
                results.append({
                    "id": aid,
                    "subject": subject,
                    "age": parsed_data["age"],
                    "sex": parsed_data["sex"],
                    "bmi": pred["bmi"],
                    "risk": pred["risk"],
                    "confidence": pred["confidence"]
                })
            except Exception as exc:
                logger.error("Inference failure on batch row %d: %s", row_idx, exc)
                errors.append({
                    "row": row_idx,
                    "subject": subject,
                    "reason": f"Inference engine failure: {str(exc)}"
                })
                
        total_eval = len(results) + len(errors)
        if total_eval == 0:
            flash("The uploaded CSV file contained no patient rows.", "err")
            return render_template("batch.html", batch_summary=None)
            
        successful = len(results)
        batch_summary = {
            "filename": file.filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total": total_eval,
            "successful": successful,
            "failed": len(errors),
            "low_count": low_count,
            "moderate_count": moderate_count,
            "high_count": high_count,
            "low_pct": round((low_count / successful) * 100, 1) if successful else 0,
            "moderate_pct": round((moderate_count / successful) * 100, 1) if successful else 0,
            "high_pct": round((high_count / successful) * 100, 1) if successful else 0,
            "results": results,
            "errors": errors
        }
        
        flash(f"Batch screening complete! Successfully stratified {successful} of {total_eval} patient records.", "ok")
        return render_template("batch.html", batch_summary=batch_summary)
        
    return render_template("batch.html", batch_summary=None)

