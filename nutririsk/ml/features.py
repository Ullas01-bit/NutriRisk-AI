"""
Feature definitions, schemas, and engineering logic for NutriRisk AI.
Used across training, inference, and explainability pipelines.
"""
import pandas as pd

# Feature lists
NUMERIC = ["age", "height_cm", "weight_kg", "bmi", "food_groups", "meals_per_day"]
CATEGORICAL = ["sex", "activity", "income", "education", "residence", "recent_illness"]
RAW = [
    "age", "sex", "height_cm", "weight_kg", "food_groups", "meals_per_day",
    "activity", "income", "education", "residence", "recent_illness"
]

# Classification target classes
LABELS = ["Low Risk", "Moderate Risk", "High Risk"]

# Explainability feature grouping (for occlusion attribution and user-facing cards)
GROUPS = {
    "Age": ["age"],
    "Sex": ["sex"],
    "BMI (Height & Weight)": ["height_cm", "weight_kg"],
    "Dietary Diversity": ["food_groups"],
    "Meal Frequency": ["meals_per_day"],
    "Physical Activity": ["activity"],
    "Household Income": ["income"],
    "Education Level": ["education"],
    "Residence (Urban/Rural)": ["residence"],
    "Recent Illness": ["recent_illness"],
}

# Categorical domain choices
CHOICES = {
    "sex": ["Female", "Male"],
    "activity": ["Low", "Moderate", "High"],
    "income": ["Low", "Middle", "High"],
    "education": ["None", "Primary", "Secondary", "Higher"],
    "residence": ["Urban", "Rural"],
    "recent_illness": ["No", "Yes"],
}

# Field validation constraints (Adults 18+)
VALIDATION_BOUNDS = {
    "age": (18, 100, "Age must be between 18 and 100 years."),
    "height_cm": (120.0, 220.0, "Height must be between 120 and 220 cm."),
    "weight_kg": (25.0, 250.0, "Weight must be between 25 and 250 kg."),
    "food_groups": (1, 8, "Food groups eaten daily must be between 1 and 8."),
    "meals_per_day": (1, 8, "Meals per day must be between 1 and 8."),
}

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies feature engineering transformations.
    Computes Body Mass Index (BMI) = weight (kg) / [height (m)]^2.
    """
    df = df.copy()
    # Ensure height is non-zero to prevent division by zero
    height_m = df["height_cm"].clip(lower=50.0) / 100.0
    df["bmi"] = (df["weight_kg"] / (height_m ** 2)).round(2)
    return df

def validate_and_parse_input(form_data: dict):
    """
    Validates form data from web assessment requests.
    Returns: (parsed_data_dict, error_message_or_None)
    """
    parsed = {}
    try:
        parsed["age"] = int(form_data.get("age", 0))
        parsed["height_cm"] = float(form_data.get("height_cm", 0.0))
        parsed["weight_kg"] = float(form_data.get("weight_kg", 0.0))
        parsed["food_groups"] = int(form_data.get("food_groups", 0))
        parsed["meals_per_day"] = int(form_data.get("meals_per_day", 0))
    except (KeyError, ValueError, TypeError):
        return None, "Please provide valid numeric values for all demographic and nutritional inputs."

    # Validate numeric ranges
    for field, (low, high, msg) in VALIDATION_BOUNDS.items():
        if not (low <= parsed[field] <= high):
            return None, msg

    # Validate categorical inputs
    for cat_field, allowed_values in CHOICES.items():
        val = form_data.get(cat_field)
        if val not in allowed_values:
            return None, f"Invalid selection '{val}' for {cat_field.replace('_', ' ')}."
        parsed[cat_field] = val

    return parsed, None
