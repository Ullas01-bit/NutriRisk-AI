import os
import json
from flask import Blueprint, render_template, current_app, session, redirect, url_for, send_from_directory, make_response
from nutririsk.db import get_db, get_active_model_metadata
from nutririsk.auth.utils import login_required
from nutririsk.ml.features import LABELS
from nutririsk.ml.data_validation import load_dataset_metadata

main_bp = Blueprint("main", __name__)

FEATURES_CATALOG = [
    {
        "name": "age",
        "label": "Patient Age",
        "category": "Demographic",
        "type": "Continuous (Integer)",
        "unit": "Years",
        "range": "18 – 100",
        "imputation": "Median (Fit on training folds only)",
        "clinical_rationale": "Sarcopenia, blunted hunger signals, physiological changes in metabolic rate and nutrient absorption in elderly cohorts."
    },
    {
        "name": "sex",
        "label": "Biological Sex",
        "category": "Demographic",
        "type": "Categorical (Binary)",
        "unit": "Nominal",
        "range": "Female, Male",
        "imputation": "Mode (Fit on training folds only)",
        "clinical_rationale": "Differences in basal metabolic rate (BMR), fat-free mass percentage, and pregnancy/lactation nutritional demands."
    },
    {
        "name": "height_cm",
        "label": "Standing Height",
        "category": "Anthropometric",
        "type": "Continuous (Float)",
        "unit": "Centimeters (cm)",
        "range": "120.0 – 220.0",
        "imputation": "Median (Fit on training folds only)",
        "clinical_rationale": "Foundational anthropometric stature metric utilized for body surface area, stunting history, and BMI denominator."
    },
    {
        "name": "weight_kg",
        "label": "Body Weight",
        "category": "Anthropometric",
        "type": "Continuous (Float)",
        "unit": "Kilograms (kg)",
        "range": "25.0 – 250.0",
        "imputation": "Median (Fit on training folds only)",
        "clinical_rationale": "Primary somatic mass indicator used to detect acute involuntary wasting and chronic protein-energy malnutrition."
    },
    {
        "name": "bmi",
        "label": "Body Mass Index (BMI)",
        "category": "Anthropometric (Engineered)",
        "type": "Continuous (Engineered)",
        "unit": "kg/m²",
        "range": "10.0 – 60.0",
        "imputation": "Deterministic engineering: weight / (height/100)²",
        "clinical_rationale": "Core WHO malnutrition index: <18.5 denotes underweight wasting; 18.5–24.9 normal; ≥30.0 indicates obesity with micronutrient risk."
    },
    {
        "name": "food_groups",
        "label": "Dietary Diversity Score",
        "category": "Nutritional",
        "type": "Discrete (Integer)",
        "unit": "Score (1–8)",
        "range": "1 – 8 food groups",
        "imputation": "Median (Fit on training folds only)",
        "clinical_rationale": "Validated proxy for micronutrient adequacy based on FAO/WHO Dietary Diversity Guidelines across major food categories."
    },
    {
        "name": "meals_per_day",
        "label": "Meal Frequency",
        "category": "Nutritional",
        "type": "Discrete (Integer)",
        "unit": "Meals / day",
        "range": "1 – 8 meals",
        "imputation": "Median (Fit on training folds only)",
        "clinical_rationale": "Surrogate for daily caloric intake regularity; skipping meals or <2 meals/day strongly correlates with acute nutritional deficits."
    },
    {
        "name": "activity",
        "label": "Physical Activity Level",
        "category": "Lifestyle",
        "type": "Categorical (Ordinal)",
        "unit": "Level",
        "range": "Low, Moderate, High",
        "imputation": "Mode (Fit on training folds only)",
        "clinical_rationale": "Determines total daily energy expenditure (TDEE) and physical mobility; low activity frequently aligns with bedridden frailty."
    },
    {
        "name": "income",
        "label": "Household Income Bracket",
        "category": "Socioeconomic",
        "type": "Categorical (Ordinal)",
        "unit": "Socioeconomic Tier",
        "range": "Low, Middle, High",
        "imputation": "Mode (Fit on training folds only)",
        "clinical_rationale": "Financial determinant of household food security, dietary variety, clean cooking fuel, and access to healthcare facilities."
    },
    {
        "name": "education",
        "label": "Educational Attainment",
        "category": "Socioeconomic",
        "type": "Categorical (Ordinal)",
        "unit": "Level",
        "range": "None, Primary, Secondary, Higher",
        "imputation": "Mode (Fit on training folds only)",
        "clinical_rationale": "Correlates with nutritional health literacy, proper hygiene practices, food preparation knowledge, and health-seeking behavior."
    },
    {
        "name": "residence",
        "label": "Geographic Residence",
        "category": "Geographic",
        "type": "Categorical (Binary)",
        "unit": "Setting",
        "range": "Urban, Rural",
        "imputation": "Mode (Fit on training folds only)",
        "clinical_rationale": "Reflects food supply chain reliability, agricultural dependency, seasonal food insecurity, and drinking water sanitation."
    },
    {
        "name": "recent_illness",
        "label": "Recent Infection / Illness",
        "category": "Clinical Health",
        "type": "Categorical (Binary)",
        "unit": "Binary",
        "range": "No, Yes",
        "imputation": "Mode (Fit on training folds only)",
        "clinical_rationale": "Acute infection episodes (diarrheal or febrile illness within 30 days) accelerate protein breakdown and induce anorexia."
    }
]

ALGORITHMS_INFO = [
    {
        "name": "Logistic Regression",
        "type": "Generalized Linear Baseline",
        "framework": "scikit-learn (LogisticRegression)",
        "regularization": "L2 Ridge Penalty (C = 1.0)",
        "strengths": "Fast deterministic convergence, highly interpretable linear log-odds, robust baseline for checking linear separability.",
        "limitations": "Underfits complex non-linear nutritional boundaries, non-monotonic BMI risk curves, and multi-way interactions."
    },
    {
        "name": "Decision Tree",
        "type": "Non-Parametric CART Tree",
        "framework": "scikit-learn (DecisionTreeClassifier)",
        "regularization": "max_depth=5, min_samples_split=10",
        "strengths": "Captures hierarchical rule sets (e.g., low BMI + high age -> High Risk); transparent decision splits.",
        "limitations": "High variance, prone to localized noise overfitting, and exhibits orthogonal decision boundaries."
    },
    {
        "name": "Random Forest",
        "type": "Bagging Bootstrap Ensemble",
        "framework": "scikit-learn (RandomForestClassifier)",
        "regularization": "n_estimators=150, max_features='sqrt'",
        "strengths": "Reduces variance via bootstrap aggregation across 150 diverse trees; highly resilient against noisy outliers.",
        "limitations": "Substantially larger disk artifact size and slower memory-intensive tree traversal."
    },
    {
        "name": "Gradient Boosting",
        "type": "Sequential Boosting Ensemble",
        "framework": "scikit-learn (GradientBoostingClassifier)",
        "regularization": "learning_rate=0.1, n_estimators=100, max_depth=3",
        "strengths": "Iteratively fits shallow trees to residual pseudo-gradients, effectively minimizing multi-class cross-entropy log-loss.",
        "limitations": "Sequential tree construction cannot be parallelized across multi-core processors as efficiently as XGBoost."
    },
    {
        "name": "XGBoost",
        "type": "Extreme Gradient Boosting",
        "framework": "xgboost (XGBClassifier)",
        "regularization": "L1 (alpha=0.1) & L2 (lambda=1.0), colsample_bytree=0.8",
        "strengths": "Exact second-order Taylor expansion gradients, weighted quantile sketch, sparsity-aware split finding, and native SHAP tree explainability.",
        "limitations": "Requires careful learning rate calibration to prevent premature leaf contraction on minority classes."
    }
]


def compute_confusion_details(matrix: list, labels: list) -> list:
    """Computes class-level TP, FP, FN, precision, recall, and support from confusion matrix."""
    if not matrix or len(matrix) != len(labels):
        return []
    details = []
    n_classes = len(labels)
    total_samples = sum(sum(row) for row in matrix)

    for i in range(n_classes):
        tp = matrix[i][i]
        actual_total = sum(matrix[i])  # Row sum
        pred_total = sum(matrix[r][i] for r in range(n_classes))  # Column sum
        fn = actual_total - tp
        fp = pred_total - tp
        tn = total_samples - tp - fn - fp

        precision = round((tp / pred_total * 100), 2) if pred_total > 0 else 0.0
        recall = round((tp / actual_total * 100), 2) if actual_total > 0 else 0.0
        specificity = round((tn / (tn + fp) * 100), 2) if (tn + fp) > 0 else 0.0

        details.append({
            "class_name": labels[i],
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "actual_support": actual_total,
            "pred_total": pred_total,
            "precision": precision,
            "recall": recall,
            "specificity": specificity
        })
    return details

def load_metrics():
    """Loads metrics.json from configured path."""
    metrics_path = current_app.config.get("METRICS_PATH")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "source": "Model not yet trained",
        "best": "None",
        "models": {},
        "importance": {},
        "class_counts": {},
        "features": []
    }

@main_bp.route("/")
def home():
    """Public landing page highlighting problem relevance, ML workflow, and project objectives."""
    metrics = load_metrics()
    return render_template("home.html", m=metrics)

@main_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Personalized User Dashboard (Prompt 14).
    Displays user profile summary, total assessments, latest risk categorization,
    historical risk distribution, longitudinal activity chart, and recent records.
    """
    db = get_db()
    uid = session["uid"]

    # 1. User Profile Summary
    user = db.execute(
        "SELECT id, name, email, role, created FROM users WHERE id = ?",
        (uid,)
    ).fetchone()

    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    # 2. Total assessments count
    total_count = db.execute(
        "SELECT COUNT(*) FROM assessments WHERE user_id = ?",
        (uid,)
    ).fetchone()[0]

    # 3. Latest assessment
    latest = None
    if total_count > 0:
        latest = db.execute(
            "SELECT * FROM assessments WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (uid,)
        ).fetchone()

    # 4. Historical risk distribution (Low, Moderate, High)
    risk_counts = {"Low Risk": 0, "Moderate Risk": 0, "High Risk": 0}
    dist_rows = db.execute(
        "SELECT risk, COUNT(*) as cnt FROM assessments WHERE user_id = ? GROUP BY risk",
        (uid,)
    ).fetchall()
    for row in dist_rows:
        if row["risk"] in risk_counts:
            risk_counts[row["risk"]] = row["cnt"]

    # Calculate percentages safely
    risk_percentages = {}
    for r_label, count in risk_counts.items():
        pct = round((count / total_count * 100), 1) if total_count > 0 else 0.0
        risk_percentages[r_label] = pct

    # 5. Assessment activity over time (grouped by date)
    timeline_rows = db.execute(
        """SELECT substr(created, 1, 10) as dt, COUNT(*) as cnt 
           FROM assessments 
           WHERE user_id = ? 
           GROUP BY dt 
           ORDER BY dt ASC""",
        (uid,)
    ).fetchall()
    activity_dates = [row["dt"] for row in timeline_rows]
    activity_counts = [row["cnt"] for row in timeline_rows]

    # 6. Recent assessment records (up to 5)
    recent_assessments = db.execute(
        """SELECT id, subject, created, risk, confidence, bmi, model_version 
           FROM assessments 
           WHERE user_id = ? 
           ORDER BY id DESC LIMIT 5""",
        (uid,)
    ).fetchall()

    metrics = load_metrics()

    return render_template(
        "dashboard.html",
        user=user,
        total_count=total_count,
        latest=latest,
        risk_counts=risk_counts,
        risk_percentages=risk_percentages,
        activity_dates=activity_dates,
        activity_counts=activity_counts,
        recent_assessments=recent_assessments,
        labels=LABELS,
        m=metrics
    )

@main_bp.route("/model")
def model_page():
    """
    Detailed ML Model Information & Technical Specification Page (Prompt 18).
    Presents end-to-end methodology, dataset provenance, candidate algorithms comparison,
    preprocessing leakage prevention, feature dictionary, permutation importance,
    and diagnostic confusion matrix for college evaluators and academic review.
    """
    metrics = load_metrics()
    dataset_meta = load_dataset_metadata()
    db = get_db()
    active_meta = get_active_model_metadata(db)

    best_model_name = metrics.get("best", "XGBoost")
    best_model_data = metrics.get("models", {}).get(best_model_name, {})
    best_confusion = best_model_data.get("confusion", [])
    confusion_details = compute_confusion_details(best_confusion, LABELS)

    return render_template(
        "model.html",
        m=metrics,
        labels=LABELS,
        dataset_meta=dataset_meta,
        active_meta=active_meta,
        features_catalog=FEATURES_CATALOG,
        algorithms_info=ALGORITHMS_INFO,
        confusion_details=confusion_details,
        best_model=best_model_name,
        best_metrics=best_model_data
    )


@main_bp.route("/manifest.json")
def manifest():
    """Serves PWA Web App Manifest for mobile and desktop app installation."""
    return send_from_directory(
        os.path.join(current_app.root_path, "static"),
        "manifest.json",
        mimetype="application/manifest+json"
    )


@main_bp.route("/sw.js")
def service_worker():
    """Serves PWA Service Worker with full root scope allowance."""
    resp = make_response(
        send_from_directory(
            os.path.join(current_app.root_path, "static"),
            "sw.js",
            mimetype="application/javascript"
        )
    )
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp

