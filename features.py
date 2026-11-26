"""
Backward-compatibility module for root-level imports.
Re-exports feature schemas and engineering functions from nutririsk.ml.features.
"""
from nutririsk.ml.features import (
    NUMERIC, CATEGORICAL, RAW, LABELS, GROUPS, CHOICES,
    add_features, validate_and_parse_input, VALIDATION_BOUNDS
)

__all__ = [
    "NUMERIC", "CATEGORICAL", "RAW", "LABELS", "GROUPS", "CHOICES",
    "add_features", "validate_and_parse_input", "VALIDATION_BOUNDS"
]
