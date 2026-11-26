"""Machine Learning sub-package for NutriRisk AI."""
from nutririsk.ml.features import (
    NUMERIC, CATEGORICAL, RAW, LABELS, GROUPS, CHOICES,
    add_features, validate_and_parse_input
)
from nutririsk.ml.prediction import predict_nutritional_risk, get_model_bundle
from nutririsk.ml.explainability import compute_occlusion_attributions
from nutririsk.ml.training import train_and_evaluate

__all__ = [
    "NUMERIC", "CATEGORICAL", "RAW", "LABELS", "GROUPS", "CHOICES",
    "add_features", "validate_and_parse_input",
    "predict_nutritional_risk", "get_model_bundle",
    "compute_occlusion_attributions", "train_and_evaluate"
]
