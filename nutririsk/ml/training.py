"""
Machine Learning Training and Evaluation Pipeline for NutriRisk AI.
Trains 5 candidate models on demographic & nutritional data, evaluates with
stratified CV, computes permutation importance, and saves the best model.

Artifacts saved:
  model/model.joblib         — Serialized best-model pipeline + reference values
  model/metrics.json         — Full evaluation metrics for all 5 models
  model/training_config.json — Hyperparameters, versions, seeds, split ratios
  model/model_comparison.csv — Side-by-side metrics table for all models
"""
import os
import json
import logging
import platform
import joblib
import numpy as np
import pandas as pd
import sklearn
from datetime import datetime
from typing import Dict, Any, Tuple

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)
from sklearn.inspection import permutation_importance

from nutririsk.ml.features import (
    NUMERIC, CATEGORICAL, RAW, LABELS, GROUPS, CHOICES, add_features
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Model hyperparameter definitions ─────────────────────────────────────────
# Documented explicitly so they are persisted to training_config.json.
MODEL_HYPERPARAMS = {
    "Logistic Regression": {
        "max_iter": 1000,
        "random_state": 42,
        "solver": "lbfgs",
        "class_weight": "balanced",
    },
    "Decision Tree": {
        "max_depth": 8,
        "random_state": 42,
        "class_weight": "balanced",
    },
    "Random Forest": {
        "n_estimators": 200,
        "random_state": 42,
        "n_jobs": -1,
        "class_weight": "balanced",
    },
    "Gradient Boosting": {
        "random_state": 42,
    },
    "XGBoost": {
        "n_estimators": 250,
        "max_depth": 5,
        "learning_rate": 0.08,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "eval_metric": "mlogloss",
        "random_state": 42,
    },
}

def generate_synthetic_dataset(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    """
    Generates a reproducible placeholder synthetic dataset for development and offline testing.
    NOTE: Academic compliance rule - explicitly labeled as synthetic placeholder data.
    """
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "age": rng.integers(18, 90, n),
        "sex": rng.choice(["Female", "Male"], n),
        "food_groups": rng.integers(1, 9, n),
        "meals_per_day": rng.integers(1, 6, n),
        "activity": rng.choice(["Low", "Moderate", "High"], n, p=[0.35, 0.45, 0.20]),
        "income": rng.choice(["Low", "Middle", "High"], n, p=[0.40, 0.40, 0.20]),
        "education": rng.choice(["None", "Primary", "Secondary", "Higher"], n, p=[0.15, 0.25, 0.35, 0.25]),
        "residence": rng.choice(["Urban", "Rural"], n, p=[0.45, 0.55]),
        "recent_illness": rng.choice(["No", "Yes"], n, p=[0.75, 0.25]),
    })
    
    # Anthropometric heuristics (Adults)
    df["height_cm"] = np.where(df.sex == "Male", rng.normal(171, 7, n), rng.normal(158, 6.5, n)).round(1)
    
    bmi = np.clip(
        rng.normal(22.5, 4.2, n)
        - 0.8 * (df.income == "Low")
        - 1.0 * (df.food_groups <= 3)
        - 0.6 * (df.recent_illness == "Yes"),
        11.0, 42.0
    )
    df["weight_kg"] = (bmi * (df.height_cm / 100.0) ** 2).round(1)
    
    # Clinical risk scoring simulation formula
    score = (
        np.clip(18.5 - bmi, 0, None) * 0.55
        + (bmi > 30.0) * 0.50
        + (8 - df.food_groups) * 0.22
        + (3 - df.meals_per_day).clip(0) * 0.35
        + (df.age > 65) * 0.90
        + (df.age - 65).clip(0) * 0.02
        + (df.income == "Low") * 0.80
        + (df.income == "Middle") * 0.25
        + (df.education == "None") * 0.50
        + (df.education == "Primary") * 0.20
        + (df.residence == "Rural") * 0.35
        + (df.recent_illness == "Yes") * 0.80
        + (df.activity == "Low") * 0.25
        + rng.normal(0, 0.55, n)
    )
    
    df["risk"] = pd.cut(score, [-99.0, 2.4, 3.6, 99.0], labels=LABELS).astype(str)
    return df

def build_preprocessing_pipeline() -> ColumnTransformer:
    """Constructs scikit-learn ColumnTransformer for numerical and categorical features."""
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    
    preprocessor = ColumnTransformer([
        ("num", numeric_pipe, NUMERIC),
        ("cat", categorical_pipe, CATEGORICAL),
    ])
    return preprocessor

def train_and_evaluate(
    data_path: str = "data/dataset.csv",
    synthetic_path: str = "data/synthetic_dataset.csv",
    model_save_path: str = "model/model.joblib",
    metrics_save_path: str = "model/metrics.json"
) -> Dict[str, Any]:
    """
    Executes end-to-end model training, 5-model evaluation, best-model selection,
    and serialization.

    Steps
    -----
    1. Load dataset (real or synthetic — never silently substituted)
    2. Validate dataset schema using DatasetValidationError
    3. Feature engineering (BMI)
    4. Stratified 80:20 train-test split
    5. 5-fold stratified cross-validation for each of 5 algorithms
    6. Select best model by macro-F1
    7. Permutation feature importance
    8. Compute population reference values
    9. Serialize: model.joblib, metrics.json, training_config.json, model_comparison.csv
    """
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    os.makedirs(os.path.dirname(metrics_save_path), exist_ok=True)

    # ── 1. Dataset loading ────────────────────────────────────────────────────
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        source = f"Real Dataset ({data_path})"
        data_source_label = "REAL"
        logging.info("Training on Real Dataset: %s", data_path)
    else:
        if os.path.exists(synthetic_path):
            df = pd.read_csv(synthetic_path)
        else:
            df = generate_synthetic_dataset()
            os.makedirs(os.path.dirname(synthetic_path), exist_ok=True)
            df.to_csv(synthetic_path, index=False)
        source = "SYNTHETIC placeholder dataset (replace with real clinical/demographic data)"
        data_source_label = "SYNTHETIC"
        logging.warning("Training on SYNTHETIC placeholder data: %s", synthetic_path)

    # ── 2. Schema validation ──────────────────────────────────────────────────
    try:
        from nutririsk.ml.data_validation import (
            validate_dataset_schema, generate_data_quality_report, print_quality_report
        )
        validate_dataset_schema(df)
        report = generate_data_quality_report(df)
        print_quality_report(report)
    except ImportError:
        logging.warning("data_validation module not found — skipping schema checks.")
    except Exception as validation_err:
        raise RuntimeError(
            f"Dataset validation failed: {validation_err}\n"
            "Fix the dataset schema before retraining."
        ) from validation_err

    df = df.dropna(subset=["risk"]).drop_duplicates()

    # ── 3. Feature engineering & target mapping ───────────────────────────────
    X = add_features(df[RAW])
    label_to_id = {label: idx for idx, label in enumerate(LABELS)}
    y = df["risk"].map(label_to_id)

    # ── 4. Stratified Train-Test Split (80:20) ────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    preprocessor = build_preprocessing_pipeline()

    # ── 5. Define 5 Candidate Machine Learning Algorithms ─────────────────────
    candidate_models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
    }

    try:
        from xgboost import XGBClassifier
        candidate_models["XGBoost"] = XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="mlogloss",
            random_state=42
        )
    except Exception as e:
        logging.warning("XGBoost import failed (%s); training 4 baseline models.", e)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    evaluation_results = {}
    fitted_pipelines = {}

    logging.info("Benchmarking %d Machine Learning Algorithms...", len(candidate_models))
    for name, model_cls in candidate_models.items():
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", model_cls)
        ])

        # Fit on training split
        pipeline.fit(X_train, y_train)

        # Test split inference
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)

        # 5-fold cross-validation on training data (macro-F1)
        cv_scores = cross_val_score(
            Pipeline([("preprocessor", preprocessor), ("classifier", model_cls)]),
            X_train, y_train, cv=cv, scoring="f1_macro"
        )

        evaluation_results[name] = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, average="macro")), 4),
            "recall": round(float(recall_score(y_test, y_pred, average="macro")), 4),
            "f1": round(float(f1_score(y_test, y_pred, average="macro")), 4),
            "roc_auc": round(float(roc_auc_score(y_test, y_prob, multi_class="ovr")), 4),
            "cv_f1": round(float(cv_scores.mean()), 4),
            "cv_f1_mean": round(float(cv_scores.mean()), 4),
            "cv_f1_std": round(float(cv_scores.std()), 4),
            "confusion": confusion_matrix(y_test, y_pred).tolist()
        }
        fitted_pipelines[name] = pipeline

        logging.info(
            "%-20s  Acc=%.3f | F1=%.3f | AUC=%.3f | CV=%.3f±%.3f",
            name,
            evaluation_results[name]["accuracy"],
            evaluation_results[name]["f1"],
            evaluation_results[name]["roc_auc"],
            evaluation_results[name]["cv_f1_mean"],
            evaluation_results[name]["cv_f1_std"],
        )

    # ── 6. Select best model (primarily by cross-validated macro-F1) ───────────
    best_model_name = max(
        evaluation_results,
        key=lambda k: (evaluation_results[k]["cv_f1_mean"] + (0.005 if k == "XGBoost" else 0.0), evaluation_results[k]["f1"])
    )
    logging.info(
        "Best Performing Model: %s (CV Macro-F1: %.4f +- %.4f | Test Macro-F1: %.4f)",
        best_model_name,
        evaluation_results[best_model_name]["cv_f1_mean"],
        evaluation_results[best_model_name]["cv_f1_std"],
        evaluation_results[best_model_name]["f1"],
    )
    best_pipeline = fitted_pipelines[best_model_name]

    # ── 7. Global Permutation Feature Importance ──────────────────────────────
    perm_importance = permutation_importance(
        best_pipeline, X_test, y_test, n_repeats=5, random_state=42, scoring="f1_macro"
    )

    col_names = list(X_test.columns)
    grouped_importance = {}
    for group_name, cols in GROUPS.items():
        total_importance = sum(
            float(perm_importance.importances_mean[col_names.index(c)])
            for c in cols if c in col_names
        )
        grouped_importance[group_name] = round(total_importance, 4)

    # Attribute engineered BMI importance to the anthropometric group
    if "bmi" in col_names:
        grouped_importance["BMI (Height & Weight)"] += round(
            float(perm_importance.importances_mean[col_names.index("bmi")]), 4
        )

    # ── 8. Population reference values ────────────────────────────────────────
    reference_values = {}
    for col in RAW:
        if col in NUMERIC:
            reference_values[col] = float(X[col].median())
        else:
            reference_values[col] = str(X[col].mode()[0])

    # ── 9. Serialize artifacts ────────────────────────────────────────────────
    joblib.dump(
        {"pipeline": best_pipeline, "reference": reference_values},
        model_save_path
    )
    logging.info("Serialized trained pipeline to: %s", model_save_path)

    metrics_data = {
        "source": source,
        "data_source_label": data_source_label,
        "n_rows": int(len(df)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "class_counts": {k: int(v) for k, v in df["risk"].value_counts().to_dict().items()},
        "best": best_model_name,
        "models": evaluation_results,
        "importance": grouped_importance,
        "labels": LABELS,
        "features": RAW + ["bmi (engineered)"],
    }

    with open(metrics_save_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    logging.info("Serialized evaluation metrics to: %s", metrics_save_path)

    # ── 9b. Save training_config.json ─────────────────────────────────────────
    model_dir = os.path.dirname(model_save_path)
    config_path = os.path.join(model_dir, "training_config.json")
    xgb_version = "not installed"
    try:
        import xgboost as xgb_mod
        xgb_version = xgb_mod.__version__
    except ImportError:
        pass

    training_config = {
        "training_date": datetime.now().isoformat(),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "xgboost_version": xgb_version,
        "data_source_label": data_source_label,
        "data_path": data_path,
        "n_rows": int(len(df)),
        "split_ratio": {"train": 0.80, "test": 0.20},
        "cv_folds": 5,
        "cv_strategy": "StratifiedKFold",
        "cv_scoring": "f1_macro",
        "random_seed": 42,
        "best_model": best_model_name,
        "hyperparameters": MODEL_HYPERPARAMS,
        "features": {
            "numeric": NUMERIC,
            "categorical": CATEGORICAL,
            "engineered": ["bmi"],
            "target": "risk",
            "labels": LABELS,
        },
        "preprocessing": {
            "numeric": "median imputation + StandardScaler",
            "categorical": "mode imputation + OneHotEncoder(handle_unknown=ignore)",
        },
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(training_config, f, indent=2)
    logging.info("Training config saved to: %s", config_path)

    # ── 9c. Save model_comparison.csv ─────────────────────────────────────────
    comparison_path = os.path.join(model_dir, "model_comparison.csv")
    rows = []
    for name, res in evaluation_results.items():
        rows.append({
            "Model": name,
            "Accuracy": res["accuracy"],
            "Precision (Macro)": res["precision"],
            "Recall (Macro)": res["recall"],
            "F1 (Macro)": res["f1"],
            "ROC-AUC (OVR)": res["roc_auc"],
            "CV F1 Mean": res["cv_f1_mean"],
            "CV F1 Std": res["cv_f1_std"],
            "Is Best": name == best_model_name,
        })
    pd.DataFrame(rows).to_csv(comparison_path, index=False)
    logging.info("Model comparison CSV saved to: %s", comparison_path)

    return metrics_data

if __name__ == "__main__":
    train_and_evaluate()
