import os
import json
import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, session, jsonify
from nutririsk.db import get_db
from nutririsk.auth.utils import login_required
from nutririsk.ml.features import LABELS
from nutririsk.routes.main import load_metrics

analytics_bp = Blueprint("analytics", __name__)

def get_empty_statistics() -> dict:
    """Returns a zeroed-out statistics dictionary when no records match."""
    return {
        "total": 0,
        "low_count": 0,
        "moderate_count": 0,
        "high_count": 0,
        "risk_counts": {"Low Risk": 0, "Moderate Risk": 0, "High Risk": 0},
        "risk_percentages": {"Low Risk": 0.0, "Moderate Risk": 0.0, "High Risk": 0.0},
        "age_labels": ["18-29", "30-44", "45-59", "60-74", "75+"],
        "age_counts": [0, 0, 0, 0, 0],
        "sex_labels": ["Female", "Male"],
        "sex_counts": [0, 0],
        "bmi_labels": ["Underweight (<18.5)", "Normal (18.5-24.9)", "Overweight (25-29.9)", "Obese (≥30)"],
        "bmi_counts": [0, 0, 0, 0],
        "trend_dates": [],
        "trend_counts": [],
        "risk_by_age": {
            "Low Risk": [0, 0, 0, 0, 0],
            "Moderate Risk": [0, 0, 0, 0, 0],
            "High Risk": [0, 0, 0, 0, 0]
        },
        "risk_by_bmi": {"Low Risk": 0.0, "Moderate Risk": 0.0, "High Risk": 0.0},
        "summary": {
            "mean_age": 0.0,
            "mean_bmi": 0.0,
            "mean_confidence": 0.0,
            "underweight_count": 0,
            "underweight_pct": 0.0,
            "high_risk_pct": 0.0
        }
    }


def calculate_statistics(where_clause: str = "", query_args: tuple = ()) -> dict:
    """
    Computes rigorous aggregated distribution and trend metrics from SQLite assessment records.
    Ensures mathematical consistency across all totals and proportions.
    """
    db = get_db()
    sql = "SELECT risk, age, sex, bmi, confidence, created FROM assessments " + where_clause
    rows = db.execute(sql, query_args).fetchall()
    
    records = [dict(r) for r in rows]
    if not records:
        return get_empty_statistics()
        
    df = pd.DataFrame(records)
    
    # Clean and cast numerical variables
    df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(40)
    df["bmi"] = pd.to_numeric(df["bmi"], errors="coerce").fillna(22.0)
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.75)
    
    total = int(len(df))
    
    # 1. Risk Tier Counts & Percentages
    r_counts = df["risk"].value_counts().reindex(LABELS, fill_value=0)
    risk_dict = {lbl: int(r_counts[lbl]) for lbl in LABELS}
    risk_pct = {
        lbl: round((risk_dict[lbl] / total * 100), 1) if total > 0 else 0.0
        for lbl in LABELS
    }
    
    # 2. Age Cohort Binning (Adult 18+)
    age_bins = pd.cut(
        df["age"],
        bins=[17, 29, 44, 59, 74, 120],
        labels=["18-29", "30-44", "45-59", "60-74", "75+"]
    )
    age_cohort_order = ["18-29", "30-44", "45-59", "60-74", "75+"]
    age_series = age_bins.value_counts().reindex(age_cohort_order, fill_value=0)
    age_counts = [int(age_series[c]) for c in age_cohort_order]
    
    # 3. Biological Sex Counts
    sex_labels = ["Female", "Male"]
    sex_series = df["sex"].value_counts()
    sex_counts = [int(sex_series.get("Female", 0)), int(sex_series.get("Male", 0))]
    
    # 4. BMI Distribution (WHO Classifications)
    bmi_labels = ["Underweight (<18.5)", "Normal (18.5-24.9)", "Overweight (25-29.9)", "Obese (≥30)"]
    bmi_bins = pd.cut(
        df["bmi"],
        bins=[0, 18.49, 24.99, 29.99, 150.0],
        labels=bmi_labels
    )
    bmi_series = bmi_bins.value_counts().reindex(bmi_labels, fill_value=0)
    bmi_counts = [int(bmi_series[cat]) for cat in bmi_labels]
    
    # 5. Assessment Trends Over Time
    date_series = df["created"].str[:10].value_counts().sort_index()
    trend_dates = list(date_series.index)
    trend_counts = [int(v) for v in date_series.values]
    
    # 6. Risk Category Comparison: Risk Tiers by Age Cohort
    ct = pd.crosstab(age_bins, df["risk"]).reindex(
        index=age_cohort_order,
        columns=LABELS,
        fill_value=0
    )
    risk_by_age = {
        lbl: [int(ct.loc[c, lbl]) for c in age_cohort_order]
        for lbl in LABELS
    }
    
    # 7. Average BMI across Risk Categories
    bmi_by_risk = df.groupby("risk")["bmi"].mean().reindex(LABELS, fill_value=0.0).round(2).to_dict()
    risk_by_bmi = {lbl: float(bmi_by_risk[lbl]) for lbl in LABELS}
    
    # 8. Summary Statistics
    underweight_count = int(bmi_series["Underweight (<18.5)"])
    underweight_pct = round((underweight_count / total * 100), 1) if total > 0 else 0.0
    high_risk_pct = risk_pct.get("High Risk", 0.0)
    
    summary = {
        "mean_age": round(float(df["age"].mean()), 1),
        "mean_bmi": round(float(df["bmi"].mean()), 2),
        "mean_confidence": round(float(df["confidence"].mean() * 100), 1),
        "underweight_count": underweight_count,
        "underweight_pct": underweight_pct,
        "high_risk_pct": high_risk_pct
    }
    
    return {
        "total": total,
        "low_count": risk_dict["Low Risk"],
        "moderate_count": risk_dict["Moderate Risk"],
        "high_count": risk_dict["High Risk"],
        "risk_counts": risk_dict,
        "risk_percentages": risk_pct,
        "age_labels": age_cohort_order,
        "age_counts": age_counts,
        "sex_labels": sex_labels,
        "sex_counts": sex_counts,
        "bmi_labels": bmi_labels,
        "bmi_counts": bmi_counts,
        "trend_dates": trend_dates,
        "trend_counts": trend_counts,
        "risk_by_age": risk_by_age,
        "risk_by_bmi": risk_by_bmi,
        "summary": summary
    }


def _build_analytics_query() -> tuple[dict, str, list, str, str, str]:
    """Helper to parse filters and build SQL condition for analytics views."""
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    scope = request.args.get("scope", "").strip()
    preset = request.args.get("preset", "").strip()
    
    today = datetime.now().date()
    if preset == "7d":
        start_date = (today - timedelta(days=7)).isoformat()
        end_date = today.isoformat()
    elif preset == "30d":
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = today.isoformat()
    elif preset == "ytd":
        start_date = f"{today.year}-01-01"
        end_date = today.isoformat()
        
    where_clauses = []
    params = []
    
    is_admin = (session.get("role") == "admin")
    if not is_admin or scope == "personal":
        where_clauses.append("user_id = ?")
        params.append(session["uid"])
        active_scope = "personal"
    else:
        active_scope = "all"
        
    if start_date:
        where_clauses.append("substr(created, 1, 10) >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("substr(created, 1, 10) <= ?")
        params.append(end_date)
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    stats = calculate_statistics(where_sql, tuple(params))
    
    return stats, active_scope, params, start_date, end_date, preset


@analytics_bp.route("/analytics")
@login_required
def analytics():
    """
    Visual healthcare analytics dashboard (Prompt 16).
    Displays KPI stat cards, risk distributions, age/sex/BMI cohorts,
    risk category comparisons, temporal trends, and summary statistics.
    """
    stats, active_scope, _, start_date, end_date, preset = _build_analytics_query()
    metrics = load_metrics()
    
    return render_template(
        "analytics.html",
        s=stats,
        m=metrics,
        labels=LABELS,
        start_date=start_date,
        end_date=end_date,
        scope=active_scope,
        preset=preset,
        is_admin=(session.get("role") == "admin")
    )


@analytics_bp.route("/api/analytics")
@login_required
def api_analytics():
    """
    JSON API endpoint returning aggregated screening statistics.
    Supports dynamic frontend asynchronous filtering.
    """
    stats, active_scope, _, start_date, end_date, preset = _build_analytics_query()
    return jsonify({
        "status": "success",
        "scope": active_scope,
        "start_date": start_date,
        "end_date": end_date,
        "preset": preset,
        "statistics": stats
    })
