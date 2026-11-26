"""
Nutritional Risk Prediction Engine for NutriRisk AI.

This module coordinates:
1. Feature extraction and Body Mass Index (BMI) engineering.
2. Dynamic loading and caching of the serialized scikit-learn / XGBoost model bundle.
3. Multi-class probability estimation across Low, Moderate, and High Risk tiers.
4. Strict alignment with the classifier's internal `classes_` ordering.
5. Local occlusion-based Explainable AI (XAI) feature attribution.
6. Graceful exception handling for missing model artifacts and malformed inputs.

ACADEMIC & CLINICAL COMPLIANCE NOTICE:
This prediction engine is an academic decision-support prototype. It generates
statistical probability estimates based on demographic, lifestyle, and dietary
inputs. It does NOT provide clinical diagnoses or replace medical professionals.
"""
import os
import logging
from typing import Dict, Any, List, Optional
import joblib
import numpy as np
import pandas as pd
from flask import current_app, has_app_context

from nutririsk.config import Config
from nutririsk.ml.features import RAW, LABELS, add_features
from nutririsk.ml.explainability import compute_occlusion_attributions, compute_shap_attributions

logger = logging.getLogger(__name__)

# In-memory pipeline cache (avoids repeated disk I/O on every web request)
_MODEL_CACHE: Dict[str, Dict[str, Any]] = {}


def get_model_bundle(model_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads and caches the serialized model bundle.
    
    The bundle contains:
      - 'pipeline': The fitted scikit-learn Pipeline (ColumnTransformer + Classifier)
      - 'reference': Dictionary of population medians and modes for occlusion explainability

    Parameters
    ----------
    model_path : str, optional
        Custom path to the serialized model file. If None, resolves from Flask
        application config or default Config.MODEL_PATH.

    Returns
    -------
    dict
        Deserialized bundle containing 'pipeline' and 'reference'.

    Raises
    ------
    FileNotFoundError
        If the model artifact does not exist on disk, providing actionable instructions.
    """
    if model_path is None:
        if has_app_context():
            model_path = current_app.config.get("MODEL_PATH", Config.MODEL_PATH)
        else:
            model_path = Config.MODEL_PATH

    # Security Validation (Prompt 21 Item 12): Guard against Path Traversal and Local File Inclusion
    from nutririsk.security import validate_safe_model_path
    canonical_model_path = validate_safe_model_path(model_path)

    if canonical_model_path in _MODEL_CACHE:
        return _MODEL_CACHE[canonical_model_path]

    if not os.path.exists(canonical_model_path):
        raise FileNotFoundError(
            f"Trained model artifact not found at '{canonical_model_path}'. "
            "Please run 'python train.py' to train and serialize the model pipeline "
            "before initiating prediction requests."
        )

    try:
        bundle = joblib.load(canonical_model_path)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to deserialize model bundle from '{canonical_model_path}': {exc}"
        ) from exc

    if not isinstance(bundle, dict) or "pipeline" not in bundle or "reference" not in bundle:
        raise ValueError(
            f"Corrupt model artifact at '{canonical_model_path}'. Expected dictionary containing "
            "'pipeline' and 'reference' keys."
        )

    _MODEL_CACHE[canonical_model_path] = bundle
    logger.info("Loaded and cached model bundle from: %s", canonical_model_path)
    return bundle


def clear_model_cache() -> None:
    """Clears the in-memory model cache, forcing reload on next prediction."""
    _MODEL_CACHE.clear()
    logger.info("Cleared in-memory model cache.")


def predict_nutritional_risk(
    input_data: Dict[str, Any],
    model_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end nutritional risk prediction pipeline.

    Execution Steps
    ---------------
    1. Input Validation Check: Verifies presence of all required raw attributes.
    2. Feature Engineering: Computes Body Mass Index (BMI = weight_kg / (height_m)^2).
    3. Pipeline Inference: ColumnTransformer handles imputation and encoding;
       the trained classifier predicts class probabilities.
    4. Probability & Class Mapping: Uses the model's actual `classes_` array to map
       probabilities to the standardized LABELS ['Low Risk', 'Moderate Risk', 'High Risk'].
    5. Stratification: Identifies the winning risk tier and model confidence score.
    6. Explainability: Computes local occlusion attributions against reference values.

    Parameters
    ----------
    input_data : dict
        Dictionary containing parsed demographic and nutritional inputs:
        age, sex, height_cm, weight_kg, food_groups, meals_per_day,
        activity, income, education, residence, recent_illness.
    model_path : str, optional
        Optional path override for the model artifact.

    Returns
    -------
    dict
        Structured result payload:
        {
            'risk': str ('Low Risk' | 'Moderate Risk' | 'High Risk'),
            'confidence': float (probability of predicted class, e.g. 0.8250),
            'probabilities': list of float (probabilities for all 3 classes in standard LABELS order),
            'class_probabilities': dict (label -> float probability),
            'bmi': float (engineered BMI rounded to 2 decimals),
            'factors': list of dict (explainability attribution drivers)
        }

    Raises
    ------
    ValueError
        If required features are missing from input_data.
    FileNotFoundError
        If the model artifact cannot be located on disk.
    """
    # 1. Verify required raw inputs
    missing_fields = [f for f in RAW if f not in input_data]
    if missing_fields:
        raise ValueError(
            f"Incomplete input data. Missing required feature(s): {missing_fields}"
        )

    # 2. Retrieve model bundle
    bundle = get_model_bundle(model_path)
    pipeline = bundle["pipeline"]
    reference = bundle["reference"]

    # 3. Construct input DataFrame and compute BMI
    raw_df = pd.DataFrame([input_data])[RAW]
    input_df = add_features(raw_df)
    calculated_bmi = float(input_df["bmi"].iloc[0])

    # 4. Predict probabilities
    raw_probs = pipeline.predict_proba(input_df)[0]

    # 5. Map probabilities according to the model's actual class ordering
    classifier = pipeline.named_steps.get("classifier")
    classes = getattr(classifier, "classes_", np.arange(len(raw_probs)))

    # Construct label-to-probability mapping based on model's internal classes_
    prob_by_label: Dict[str, float] = {}
    for idx, class_id in enumerate(classes):
        if isinstance(class_id, (int, np.integer)):
            if 0 <= class_id < len(LABELS):
                label_name = LABELS[class_id]
            else:
                label_name = f"Class_{class_id}"
        else:
            label_name = str(class_id)
        prob_by_label[label_name] = float(raw_probs[idx])

    # Ensure all three standard LABELS are represented in canonical order
    canonical_probs = [
        round(prob_by_label.get(label, 0.0), 4)
        for label in LABELS
    ]

    # Normalize if minor floating point drift occurred
    prob_sum = sum(canonical_probs)
    if prob_sum > 0:
        canonical_probs = [round(p / prob_sum, 4) for p in canonical_probs]

    # 6. Stratification and Confidence
    predicted_idx = int(np.argmax(canonical_probs))
    predicted_label = LABELS[predicted_idx]
    confidence = float(canonical_probs[predicted_idx])

    # 7. Local Explainability (Occlusion Attribution)
    factors = compute_occlusion_attributions(
        pipeline=pipeline,
        reference_values=reference,
        input_dict=input_data,
        predicted_class_idx=predicted_idx,
        predicted_prob=confidence
    )

    # 8. Optional Advanced SHAP Attribution (TreeExplainer)
    shap_results = compute_shap_attributions(
        pipeline=pipeline,
        input_dict=input_data,
        predicted_class_idx=predicted_idx
    )

    return {
        "risk": predicted_label,
        "confidence": confidence,
        "probabilities": canonical_probs,
        "class_probabilities": {
            label: prob for label, prob in zip(LABELS, canonical_probs)
        },
        "factors": factors,
        "shap": shap_results,
        "bmi": calculated_bmi
    }
