"""
Dataset Validation Module for NutriRisk AI.

Provides schema validation, data quality checks, provenance verification,
and structured quality reporting before training or inference.

IMPORTANT: This module enforces academic integrity rules:
- Real dataset must pass all schema checks before use
- Synthetic data must never be substituted silently
- Class labels must have documented clinical provenance
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from nutririsk.ml.features import CHOICES, LABELS, RAW, VALIDATION_BOUNDS

logger = logging.getLogger(__name__)

# ── Required columns ─────────────────────────────────────────────────────────
REQUIRED_COLUMNS: List[str] = RAW + ["risk"]

# ── Custom exception ──────────────────────────────────────────────────────────
class DatasetValidationError(ValueError):
    """Raised when a dataset fails schema or quality validation.

    The error message contains a human-readable explanation of every
    failing check so users know exactly what to fix.
    """


# ─────────────────────────────────────────────────────────────────────────────
# Individual check functions
# ─────────────────────────────────────────────────────────────────────────────

def validate_dataset_schema(df: pd.DataFrame) -> None:
    """Verify that the DataFrame contains all required columns.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset to inspect.

    Raises
    ------
    DatasetValidationError
        If any required column is absent.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DatasetValidationError(
            f"Dataset is missing {len(missing)} required column(s): "
            f"{missing}.\n"
            f"The dataset must include all RAW features plus the 'risk' label column.\n"
            f"Required columns: {REQUIRED_COLUMNS}"
        )
    logger.info("Schema check passed: all %d required columns present.", len(REQUIRED_COLUMNS))


def check_missing_values(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Count missing (NaN) values per column.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    dict
        ``{column: {"count": int, "pct": float}}`` for every column that
        has at least one missing value, plus an ``"_total"`` summary key.
    """
    result: Dict[str, Any] = {}
    total_cells = len(df)
    total_missing = 0
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n > 0:
            result[col] = {"count": n, "pct": round(n / total_cells * 100, 2)}
            total_missing += n
    result["_total"] = {"count": total_missing, "pct": round(total_missing / (total_cells * len(df.columns)) * 100, 2)}
    logger.info("Missing-value check: %d cell(s) missing across %d column(s).",
                total_missing, len([k for k in result if k != "_total"]))
    return result


def check_duplicates(df: pd.DataFrame) -> Dict[str, int]:
    """Count fully-duplicated rows.

    Returns
    -------
    dict
        ``{"duplicate_rows": int, "total_rows": int, "unique_rows": int}``
    """
    n_dup = int(df.duplicated().sum())
    result = {
        "duplicate_rows": n_dup,
        "total_rows": len(df),
        "unique_rows": len(df) - n_dup,
    }
    logger.info("Duplicate check: %d duplicate row(s) found.", n_dup)
    return result


def check_value_ranges(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Validate numeric feature values against VALIDATION_BOUNDS.

    Returns
    -------
    dict
        Per-feature dict with ``{min, max, violations}`` where
        ``violations`` is the count of out-of-range rows.
    """
    result: Dict[str, Any] = {}
    for col, (lo, hi, _) in VALIDATION_BOUNDS.items():
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        violations = int(((series < lo) | (series > hi)).sum())
        result[col] = {
            "expected_min": lo,
            "expected_max": hi,
            "actual_min": round(float(series.min()), 3) if not series.isna().all() else None,
            "actual_max": round(float(series.max()), 3) if not series.isna().all() else None,
            "violations": violations,
        }
        if violations:
            logger.warning("Range check: %d violation(s) in column '%s'.", violations, col)
    return result


def check_categorical_values(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Detect invalid categorical values outside CHOICES domains.

    Returns
    -------
    dict
        ``{feature: {"expected": list, "unexpected": list, "violation_count": int}}``
    """
    result: Dict[str, Any] = {}
    for col, allowed in CHOICES.items():
        if col not in df.columns:
            continue
        unique_vals = set(df[col].dropna().unique())
        unexpected = sorted(unique_vals - set(allowed))
        result[col] = {
            "expected_values": allowed,
            "unexpected_values": unexpected,
            "violation_count": int(df[col].isin(unexpected).sum()) if unexpected else 0,
        }
        if unexpected:
            logger.warning("Categorical check: unexpected values %s in '%s'.", unexpected, col)
    return result


def check_class_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyse risk label distribution and flag class imbalance.

    Returns
    -------
    dict
        ``{label: count}`` plus ``"unknown_labels"`` and ``"imbalance_ratio"``
        (max_count / min_count; values > 3 are flagged as imbalanced).
    """
    if "risk" not in df.columns:
        return {"error": "Column 'risk' not found."}

    counts = df["risk"].value_counts().to_dict()
    result: Dict[str, Any] = {label: int(counts.get(label, 0)) for label in LABELS}
    unknown = [v for v in counts if v not in LABELS]
    result["unknown_labels"] = unknown

    known_counts = [result[l] for l in LABELS if result[l] > 0]
    if len(known_counts) >= 2:
        ratio = round(max(known_counts) / min(known_counts), 2)
        result["imbalance_ratio"] = ratio
        result["is_imbalanced"] = ratio > 3.0
    else:
        result["imbalance_ratio"] = None
        result["is_imbalanced"] = True  # Only one class present — severe issue

    logger.info("Class distribution: %s", {l: result[l] for l in LABELS})
    return result


def check_adult_scope(df: pd.DataFrame) -> Dict[str, Any]:
    """Verify all age values satisfy the adult-only scope (≥ 18).

    Returns
    -------
    dict
        ``{"minors_found": int, "min_age": float, "max_age": float}``
    """
    if "age" not in df.columns:
        return {"error": "Column 'age' not found."}
    ages = pd.to_numeric(df["age"], errors="coerce")
    minors = int((ages < 18).sum())
    result = {
        "minors_found": minors,
        "min_age": float(ages.min()) if not ages.isna().all() else None,
        "max_age": float(ages.max()) if not ages.isna().all() else None,
    }
    if minors:
        logger.warning("Adult-scope check: %d minor(s) found (age < 18).", minors)
    return result


def check_risk_label_origin(
    df: pd.DataFrame,
    metadata_path: str,
) -> Dict[str, Any]:
    """Validate that risk labels have documented clinical provenance.

    Parameters
    ----------
    df : pd.DataFrame
    metadata_path : str
        Path to ``dataset_metadata.json``.

    Returns
    -------
    dict
        Provenance metadata or error information.
    """
    result: Dict[str, Any] = {}

    if not os.path.exists(metadata_path):
        result["metadata_found"] = False
        result["warning"] = (
            f"Provenance metadata file not found at '{metadata_path}'. "
            "Please create this file before using a real dataset in production. "
            "See 'data/dataset_metadata.json' template."
        )
        logger.warning("Provenance metadata missing at: %s", metadata_path)
        return result

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    result["metadata_found"] = True
    result["is_real_data"] = metadata.get("is_real_data", False)
    result["source"] = metadata.get("source", "Unknown")
    result["license"] = metadata.get("license", "Unknown")
    result["risk_labeling_methodology"] = metadata.get("risk_labeling_methodology", "Not documented")
    result["labeling_reference"] = metadata.get("labeling_reference", "Not documented")
    result["population_description"] = metadata.get("population_description", "Not documented")

    if not result["is_real_data"]:
        result["warning"] = (
            "Metadata indicates this is NOT real clinical data. "
            "Ensure 'is_real_data' is set to true only when a verified research "
            "dataset with ethical clearance is integrated."
        )

    logger.info("Provenance check: source='%s', is_real_data=%s",
                result["source"], result["is_real_data"])
    return result


def check_potential_leakage(df: pd.DataFrame) -> Dict[str, Any]:
    """Identify columns that are highly correlated with the target label
    and may represent data leakage.

    Returns
    -------
    dict
        Suspiciously correlated features with Cramér-V statistic.
    """
    if "risk" not in df.columns:
        return {"error": "Column 'risk' not found."}

    suspicious: Dict[str, float] = {}
    y = df["risk"].astype("category").cat.codes

    for col in df.columns:
        if col == "risk":
            continue
        x = df[col]
        if pd.api.types.is_numeric_dtype(x):
            corr = abs(float(pd.to_numeric(x, errors="coerce").fillna(0).corr(y)))
            if corr > 0.85:
                suspicious[col] = round(corr, 4)
        else:
            # Chi-squared-based Cramér-V approximation
            from itertools import product as iproduct
            ct = pd.crosstab(x.fillna("__NA__"), df["risk"])
            n = ct.values.sum()
            if n == 0:
                continue
            chi2 = float(
                ((ct - ct.values.sum(axis=1, keepdims=True) * ct.values.sum(axis=0, keepdims=True) / n) ** 2
                 / (ct.values.sum(axis=1, keepdims=True) * ct.values.sum(axis=0, keepdims=True) / n + 1e-9)
                 ).values.sum()
            )
            k = min(ct.shape) - 1
            cramers_v = float(np.sqrt(chi2 / (n * max(k, 1))))
            if cramers_v > 0.85:
                suspicious[col] = round(cramers_v, 4)

    result: Dict[str, Any] = {
        "suspicious_features": suspicious,
        "leakage_risk": "HIGH" if suspicious else "LOW",
    }
    if suspicious:
        logger.warning("Potential data leakage detected in: %s", list(suspicious.keys()))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Master quality report
# ─────────────────────────────────────────────────────────────────────────────

def generate_data_quality_report(
    df: pd.DataFrame,
    metadata_path: str = "data/dataset_metadata.json",
) -> Dict[str, Any]:
    """Run all validation checks and return a structured quality report.

    This function does NOT raise an exception — it collects all findings.
    Call ``validate_dataset_schema`` separately if you need early failure.

    Parameters
    ----------
    df : pd.DataFrame
        The dataset to inspect.
    metadata_path : str
        Path to provenance metadata JSON.

    Returns
    -------
    dict
        Structured quality report with keys:
        ``schema``, ``missing_values``, ``duplicates``, ``value_ranges``,
        ``categorical_values``, ``class_distribution``, ``adult_scope``,
        ``provenance``, ``leakage``, ``summary``.
    """
    logger.info("-" * 60)
    logger.info("Starting data quality validation for dataset (%d rows x %d cols)",
                len(df), len(df.columns))

    report: Dict[str, Any] = {}

    # 1. Schema
    schema_errors: List[str] = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    report["schema"] = {
        "required_columns": REQUIRED_COLUMNS,
        "present_columns": list(df.columns),
        "missing_columns": schema_errors,
        "passed": len(schema_errors) == 0,
    }

    # 2. Missing values
    report["missing_values"] = check_missing_values(df)

    # 3. Duplicates
    report["duplicates"] = check_duplicates(df)

    # 4. Value ranges (numeric)
    report["value_ranges"] = check_value_ranges(df)

    # 5. Categorical domains
    report["categorical_values"] = check_categorical_values(df)

    # 6. Class distribution
    report["class_distribution"] = check_class_distribution(df)

    # 7. Adult scope
    report["adult_scope"] = check_adult_scope(df)

    # 8. Provenance / label origin
    report["provenance"] = check_risk_label_origin(df, metadata_path)

    # 9. Potential leakage
    report["leakage"] = check_potential_leakage(df)

    # 10. Summary banner
    warnings: List[str] = []
    if not report["schema"]["passed"]:
        warnings.append(f"SCHEMA ERROR: Missing columns {schema_errors}")
    missing_total = report["missing_values"].get("_total", {}).get("count", 0)
    if missing_total > 0:
        warnings.append(f"MISSING VALUES: {missing_total} missing cell(s) detected — imputation will be applied.")
    if report["duplicates"]["duplicate_rows"] > 0:
        warnings.append(f"DUPLICATES: {report['duplicates']['duplicate_rows']} duplicate row(s) — consider deduplication.")
    for col, info in report["value_ranges"].items():
        if info.get("violations", 0) > 0:
            warnings.append(f"RANGE VIOLATION: {info['violations']} out-of-range value(s) in '{col}'.")
    for col, info in report["categorical_values"].items():
        if info.get("violation_count", 0) > 0:
            warnings.append(f"INVALID CATEGORY: {info['violation_count']} invalid value(s) in '{col}'.")
    if report["class_distribution"].get("is_imbalanced"):
        warnings.append("CLASS IMBALANCE: Imbalance ratio > 3. Class-weighted training is recommended.")
    if report["adult_scope"].get("minors_found", 0) > 0:
        warnings.append(f"SCOPE VIOLATION: {report['adult_scope']['minors_found']} minor(s) (age < 18) in dataset.")
    if not report.get("provenance", {}).get("metadata_found", False):
        warnings.append("PROVENANCE: Metadata file missing — label origin not documented.")
    if report["leakage"]["leakage_risk"] == "HIGH":
        warnings.append(f"LEAKAGE RISK: Suspicious features: {list(report['leakage']['suspicious_features'].keys())}.")

    report["summary"] = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "warnings": warnings,
        "passed": len(warnings) == 0,
        "is_suitable_for_training": (
            report["schema"]["passed"]
            and report["adult_scope"].get("minors_found", 0) == 0
            and report["class_distribution"].get("is_imbalanced", True) is not True
        ),
    }

    logger.info("Data quality report generated -- %d warning(s).", len(warnings))
    logger.info("-" * 60)
    return report


def print_quality_report(report: Dict[str, Any]) -> None:
    """Print a human-readable summary of the data quality report to stdout."""
    print("\n" + "=" * 65)
    print("  NutriRisk AI -- Dataset Quality Report")
    print("=" * 65)
    s = report.get("summary", {})
    print(f"  Rows    : {s.get('total_rows', '?')}")
    print(f"  Columns : {s.get('total_columns', '?')}")
    print(f"  Overall : {'[PASSED]' if s.get('passed') else '[WARNINGS FOUND]'}")
    print(f"  Training: {'SUITABLE' if s.get('is_suitable_for_training') else 'NOT SUITABLE - fix issues first'}")

    warnings = s.get("warnings", [])
    if warnings:
        print("\n  [!] Issues Detected:")
        for w in warnings:
            print(f"     * {w}")

    cd = report.get("class_distribution", {})
    print("\n  Class Distribution:")
    from nutririsk.ml.features import LABELS
    for label in LABELS:
        count = cd.get(label, 0)
        print(f"     {label:<16} : {count:,}")

    prov = report.get("provenance", {})
    print("\n  Provenance:")
    print(f"     Source   : {prov.get('source', 'Unknown')}")
    print(f"     License  : {prov.get('license', 'Unknown')}")
    print(f"     Real Data: {prov.get('is_real_data', False)}")

    print("=" * 65 + "\n")


def load_dataset_metadata(meta_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads dataset provenance and validation metadata from data/dataset_metadata.json."""
    if meta_path is None:
        meta_path = os.path.join("data", "dataset_metadata.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not read dataset metadata: %s", e)
    return {
        "source": "SYNTHETIC placeholder dataset (programmatically generated)",
        "license": "Academic Evaluation License",
        "is_real_data": False,
        "n_subjects": 6000,
        "population_description": "Simulated adult population (age 18–90)",
        "known_limitations": [
            "Algorithmic score heuristics",
            "Requires empirical clinical survey validation"
        ],
        "preprocessing_decisions": [
            "Median imputation for numeric features",
            "Mode imputation for categorical features",
            "StandardScaler for continuous normalization",
            "OneHotEncoder for categorical encoding",
            "Deterministic BMI feature engineering",
            "Stratified 80:20 split with 5-fold cross-validation"
        ]
    }

