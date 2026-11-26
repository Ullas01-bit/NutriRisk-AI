"""
Train and benchmark machine learning models on the real-world macro country-level dataset
(FAO Undernourishment, Global Hunger Index, UNICEF Underweight).
"""
import os
import sys
import json
import logging
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def train_macro():
    macro_path = "data/real_world_macro_dataset.csv"
    if not os.path.exists(macro_path):
        logging.error("Macro dataset %s not found.", macro_path)
        return

    df = pd.read_csv(macro_path)
    logging.info("Loaded real-world macro dataset: %d rows x %d cols", len(df), len(df.columns))

    # Features: continent, year, undernourishment_pct, underweight_pct
    # Target: risk
    feature_cols = ["continent", "year", "undernourishment_pct", "underweight_pct"]
    df_clean = df.dropna(subset=["risk"]).copy()

    X = df_clean[feature_cols]
    y = df_clean["risk"]

    num_cols = ["year", "undernourishment_pct", "underweight_pct"]
    cat_cols = ["continent"]

    preprocessor = ColumnTransformer([
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ]), num_cols),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]), cat_cols)
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(max_depth=6, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=150, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42)
    }

    try:
        from xgboost import XGBClassifier
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y_train_enc = le.fit_transform(y_train)
        y_test_enc = le.transform(y_test)
        has_xgb = True
    except ImportError:
        has_xgb = False

    results = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, clf in models.items():
        pipe = Pipeline([
            ("prep", preprocessor),
            ("clf", clf)
        ])
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        y_prob = pipe.predict_proba(X_test)

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro")
        try:
            auc = roc_auc_score(pd.get_dummies(y_test), y_prob, multi_class="ovr")
        except Exception:
            auc = 0.0

        cv_scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="f1_macro")

        results[name] = {
            "accuracy": round(float(acc), 4),
            "macro_f1": round(float(f1), 4),
            "roc_auc": round(float(auc), 4),
            "cv_f1_mean": round(float(cv_scores.mean()), 4),
            "cv_f1_std": round(float(cv_scores.std()), 4)
        }
        logging.info("%-20s Acc=%.4f | F1=%.4f | AUC=%.4f | CV=%.4f+-%.4f",
                     name, acc, f1, auc, cv_scores.mean(), cv_scores.std())

    out_file = "model/real_world_macro_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "source": "Empirical Multi-National FAO/GHI/UNICEF Country-Level Dataset",
            "n_records": len(df_clean),
            "countries_covered": int(df_clean["country"].nunique()),
            "years_covered": f"{int(df_clean['year'].min())}-{int(df_clean['year'].max())}",
            "models": results
        }, f, indent=2)
    logging.info("Saved macro country-level metrics to %s", out_file)

if __name__ == "__main__":
    train_macro()
