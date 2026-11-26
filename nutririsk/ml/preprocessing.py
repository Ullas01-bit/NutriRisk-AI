"""
Preprocessing Module for NutriRisk AI.

Encapsulates all scikit-learn feature preprocessing, feature engineering (BMI),
train-test splitting, and stratified cross-validation.

Key Design Principles & Data Leakage Prevention:
1. BMI feature engineering is deterministic (computed per row before model fitting).
2. Numerical imputation (median) and scaling (StandardScaler) are fitted STRICTLY
   on training splits/folds within scikit-learn Pipeline objects.
3. Categorical imputation (mode) and encoding (OneHotEncoder) are fitted STRICTLY
   on training splits/folds within scikit-learn Pipeline objects.
4. Stratified 80:20 train-test splitting preserves class distribution.
5. 5-fold stratified cross-validation evaluates generalization without data leakage.
"""
import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, StratifiedKFold

from nutririsk.ml.features import (
    NUMERIC, CATEGORICAL, RAW, LABELS, CHOICES, VALIDATION_BOUNDS, add_features
)

logger = logging.getLogger(__name__)


def build_preprocessing_pipeline() -> ColumnTransformer:
    """
    Constructs scikit-learn ColumnTransformer for numerical and categorical features.
    
    Numeric pipeline:
      - SimpleImputer(strategy='median')
      - StandardScaler()
      
    Categorical pipeline:
      - SimpleImputer(strategy='most_frequent')
      - OneHotEncoder(handle_unknown='ignore')
      
    Returns
    -------
    ColumnTransformer
    """
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


def prepare_features_and_target(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.Series, Dict[str, int]]:
    """
    Prepares input DataFrame for model training:
    1. Removes rows with missing target label.
    2. Removes fully duplicated records.
    3. Adds engineered BMI feature.
    4. Extracts feature matrix X (RAW + bmi) and integer-encoded target vector y.
    
    Returns
    -------
    X : pd.DataFrame
        Engineered feature matrix.
    y : pd.Series
        Integer-encoded target vector (0: Low Risk, 1: Moderate Risk, 2: High Risk).
    label_to_id : dict
        Mapping from text label to integer ID.
    """
    df_clean = df.dropna(subset=["risk"]).drop_duplicates()
    X = add_features(df_clean[RAW])
    label_to_id = {label: idx for idx, label in enumerate(LABELS)}
    y = df_clean["risk"].map(label_to_id).astype(int)
    
    logger.info(
        "Prepared dataset: %d valid samples across %d features.",
        len(X), X.shape[1]
    )
    return X, y, label_to_id


def split_data(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.20,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Performs stratified train-test split (default 80:20) using a reproducible random seed.
    Stratification ensures equal representation of Low, Moderate, and High risk cases.
    
    Returns
    -------
    X_train, X_test, y_train, y_test
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    logger.info(
        "Data split: Train=%d (%.1f%%), Test=%d (%.1f%%)",
        len(X_train), (1 - test_size) * 100,
        len(X_test), test_size * 100
    )
    return X_train, X_test, y_train, y_test


def get_stratified_cv(
    n_splits: int = 5,
    random_state: int = 42
) -> StratifiedKFold:
    """
    Returns a StratifiedKFold cross-validator with shuffling and a fixed seed.
    """
    return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
