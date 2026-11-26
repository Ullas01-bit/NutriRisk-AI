"""
Explainable AI (XAI) Engine for NutriRisk AI.

This module provides two complementary interpretability paradigms:
1. Occlusion-Based Sensitivity Analysis (Primary Baseline XAI):
   Measures the delta shift in predicted-class posterior probability when an
   individual's feature group is substituted with the population baseline (median/mode).
2. SHAP (SHapley Additive exPlanations - Advanced Game-Theoretic XAI):
   Computes exact Shapley values via TreeExplainer / LinearExplainer, attributing
   model output in margin space and mapping one-hot features back to human-readable names.

Both methods provide non-diagnostic, decision-support explanations.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from nutririsk.ml.features import RAW, GROUPS, LABELS, add_features

logger = logging.getLogger(__name__)

# Cache for SHAP explainers (avoid reconstructing expensive tree structures on every request)
_SHAP_EXPLAINER_CACHE: Dict[int, Any] = {}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Human-Readable Explanation Text Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_human_readable_explanation(
    group_name: str,
    input_dict: Dict[str, Any],
    reference_values: Dict[str, Any],
    effect: float,
    predicted_label: str
) -> str:
    """
    Constructs a plain-language explanation for a given clinical indicator group,
    contrasting the user's observed values with population baselines.
    """
    is_risk_driver = effect > 0

    if group_name == "BMI (Height & Weight)":
        height_m = float(input_dict.get("height_cm", 170.0)) / 100.0
        weight_kg = float(input_dict.get("weight_kg", 65.0))
        bmi = round(weight_kg / (height_m ** 2), 1)
        ref_h = float(reference_values.get("height_cm", 165.0)) / 100.0
        ref_w = float(reference_values.get("weight_kg", 65.0))
        ref_bmi = round(ref_w / (ref_h ** 2), 1)

        if bmi < 18.5:
            return (
                f"Calculated BMI of {bmi} kg/m² indicates underweight status "
                f"(population reference: {ref_bmi} kg/m²), which significantly increases nutritional vulnerability."
            )
        elif bmi >= 30.0:
            return (
                f"Calculated BMI of {bmi} kg/m² indicates obesity "
                f"(population reference: {ref_bmi} kg/m²), contributing to metabolic risk elevation."
            )
        elif 18.5 <= bmi < 25.0:
            return (
                f"Calculated BMI of {bmi} kg/m² falls within the healthy reference range (18.5–24.9 kg/m²), "
                f"serving as a protective physical buffer."
            )
        else:
            return f"Calculated BMI of {bmi} kg/m² is slightly above standard baseline ({ref_bmi} kg/m²)."

    elif group_name == "Dietary Diversity":
        fg = int(input_dict.get("food_groups", 4))
        ref_fg = int(reference_values.get("food_groups", 5))
        if fg <= 3:
            return (
                f"Dietary intake across only {fg} food group(s) daily is below the population median of {ref_fg}, "
                f"indicating restricted micronutrient diversity."
            )
        elif fg >= 6:
            return (
                f"Diverse diet spanning {fg} food groups (population median: {ref_fg}) provides robust nutritional support."
            )
        else:
            return f"Consuming {fg} food groups daily aligns with average dietary diversity ({ref_fg} groups)."

    elif group_name == "Meal Frequency":
        meals = int(input_dict.get("meals_per_day", 3))
        ref_meals = int(reference_values.get("meals_per_day", 3))
        if meals <= 2:
            return f"Low meal frequency ({meals} meal(s)/day) may lead to inadequate caloric and macronutrient intake."
        elif meals >= 4:
            return f"Regular meal pattern of {meals} meals/day supports steady energy and nutrient delivery."
        else:
            return f"Meal frequency of {meals} meals/day matches standard population pattern ({ref_meals}/day)."

    elif group_name == "Recent Illness":
        illness = str(input_dict.get("recent_illness", "No"))
        if illness == "Yes":
            return "Acute illness reported in the past 14 days causes temporary metabolic depletion and elevated risk."
        else:
            return "Absence of recent acute illness protects nutritional stability."

    elif group_name == "Age":
        age = int(input_dict.get("age", 40))
        ref_age = int(reference_values.get("age", 50))
        if age >= 65:
            return f"Advanced age ({age} years) increases susceptibility to sarcopenia and reduced metabolic reserve."
        elif age <= 30:
            return f"Young adult age ({age} years) is associated with higher metabolic resilience."
        else:
            return f"Age of {age} years is consistent with adult cohort averages."

    elif group_name == "Physical Activity":
        act = str(input_dict.get("activity", "Moderate"))
        if act == "Low":
            return "Low physical activity indicates a sedentary lifestyle, lowering overall functional capacity."
        elif act == "High":
            return "High physical activity level maintains muscular mass and metabolic health."
        else:
            return "Moderate physical activity provides adequate baseline fitness."

    elif group_name == "Household Income":
        inc = str(input_dict.get("income", "Middle"))
        if inc == "Low":
            return "Low household income creates socio-economic constraints on consistent access to nutrient-dense foods."
        elif inc == "High":
            return "High household income facilitates dependable access to diverse nutritional resources."
        else:
            return "Middle-income level represents average food security conditions."

    elif group_name == "Education Level":
        edu = str(input_dict.get("education", "Secondary"))
        if edu in ("None", "Primary"):
            return f"Educational attainment ({edu}) correlates with reduced access to nutritional health information."
        else:
            return f"Educational attainment ({edu}) supports informed health literacy and dietary choices."

    elif group_name == "Residence (Urban/Rural)":
        res = str(input_dict.get("residence", "Urban"))
        if res == "Rural":
            return "Rural residence may pose logistical constraints on specialized dietary varieties and clinical facilities."
        else:
            return "Urban residence provides greater physical proximity to fresh food markets and healthcare."

    elif group_name == "Sex":
        sex = str(input_dict.get("sex", "Female"))
        return f"Biological sex ({sex}) contextualizes anthropometric baseline expectations."

    return (
        f"Contributes {'towards' if is_risk_driver else 'away from'} {predicted_label} "
        f"with an effect delta of {abs(effect):.4f}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Occlusion-Based Sensitivity Analysis (Baseline Method)
# ─────────────────────────────────────────────────────────────────────────────

def compute_occlusion_attributions(
    pipeline: Any,
    reference_values: Dict[str, Any],
    input_dict: Dict[str, Any],
    predicted_class_idx: int,
    predicted_prob: float
) -> List[Dict[str, Any]]:
    """
    Computes local feature contribution via occlusion sensitivity analysis.

    Methodology:
    For each clinical indicator group, the individual's reported values are replaced
    with the population reference baseline (median for numeric, mode for categorical).
    The delta drop in posterior probability for the predicted risk class is computed:
        Delta_P = P_observed - P_occluded

    Interpretation:
    - Delta_P > 0: The individual's value increases probability of the predicted risk tier (Risk Driver).
    - Delta_P < 0: The individual's value dampens probability of the predicted risk tier (Protective Buffer).

    Returns
    -------
    list of dict
        Sorted by absolute importance share, each with:
        'name', 'effect', 'share', 'direction', 'arrow', 'explanation'
    """
    predicted_label = LABELS[predicted_class_idx]
    factors = []

    for group_name, cols in GROUPS.items():
        # Clone input and replace current group feature(s) with baseline
        occluded_input = dict(input_dict)
        for col in cols:
            occluded_input[col] = reference_values[col]

        occluded_df = add_features(pd.DataFrame([occluded_input])[RAW])
        prob_occluded = float(pipeline.predict_proba(occluded_df)[0][predicted_class_idx])

        # Delta P: positive means user's value drives probability toward the predicted class
        delta = float(predicted_prob - prob_occluded)
        factors.append((group_name, delta))

    total_abs_impact = sum(abs(v) for _, v in factors) or 1.0

    formatted_factors = []
    for name, val in factors:
        share = round(100.0 * abs(val) / total_abs_impact, 1)
        direction = "Pushes toward risk" if val > 0 else "Protective buffer"
        arrow = "▲" if val > 0 else "▼"
        explanation = generate_human_readable_explanation(
            name, input_dict, reference_values, val, predicted_label
        )
        formatted_factors.append({
            "name": name,
            "effect": round(val, 4),
            "share": share,
            "direction": direction,
            "arrow": arrow,
            "explanation": explanation
        })

    # Sort descending by relative share
    formatted_factors.sort(key=lambda x: -x["share"])
    return formatted_factors


# ─────────────────────────────────────────────────────────────────────────────
# 3. SHAP (SHapley Additive exPlanations) Module
# ─────────────────────────────────────────────────────────────────────────────

def get_clean_feature_name(transformed_name: str) -> str:
    """
    Converts scikit-learn OneHot/StandardScaler feature names into human-readable labels.
    Example: 'cat__recent_illness_Yes' -> 'Recent Illness: Yes'
             'num__bmi' -> 'Body Mass Index (BMI)'
    """
    name = transformed_name.replace("num__", "").replace("cat__", "")
    
    clean_map = {
        "age": "Age",
        "height_cm": "Height (cm)",
        "weight_kg": "Weight (kg)",
        "bmi": "Body Mass Index (BMI)",
        "food_groups": "Dietary Diversity (Food Groups)",
        "meals_per_day": "Meal Frequency (Meals/Day)",
    }
    if name in clean_map:
        return clean_map[name]
        
    # Categoricals with underscore values, e.g. 'activity_Low' -> 'Physical Activity: Low'
    if "_" in name:
        parts = name.split("_")
        col_part = "_".join(parts[:-1])
        val_part = parts[-1]
        readable_col = col_part.replace("_", " ").title()
        return f"{readable_col}: {val_part}"
        
    return name.replace("_", " ").title()


def compute_shap_attributions(
    pipeline: Any,
    input_dict: Dict[str, Any],
    predicted_class_idx: int
) -> Optional[Dict[str, Any]]:
    """
    Computes local SHAP (SHapley Additive exPlanations) values for the predicted class.

    Methodology:
    Uses `shap.TreeExplainer` on the fitted tree classifier (XGBoost, Random Forest, etc.)
    applied to the output of the fitted `ColumnTransformer`.
    Maps transformed one-hot features back to understandable feature names and aggregates
    attributions into intuitive clinical indicator groups.

    Parameters
    ----------
    pipeline : scikit-learn Pipeline
        Fitted model pipeline (preprocessor + classifier).
    input_dict : dict
        Raw parsed inputs from user.
    predicted_class_idx : int
        Index (0, 1, or 2) of the predicted risk tier.

    Returns
    -------
    dict or None
        Structured SHAP result dictionary, or None if SHAP is unavailable.
    """
    try:
        import shap
    except ImportError:
        logger.warning("SHAP library is not installed. Skipping SHAP explanation.")
        return None

    try:
        preprocessor = pipeline.named_steps.get("preprocessor")
        classifier = pipeline.named_steps.get("classifier")

        if preprocessor is None or classifier is None:
            logger.warning("Pipeline missing preprocessor or classifier component.")
            return None

        # Transform single input instance
        input_df = add_features(pd.DataFrame([input_dict])[RAW])
        X_trans = preprocessor.transform(input_df)

        # Retrieve transformed feature names
        try:
            raw_feature_names = preprocessor.get_feature_names_out()
        except Exception:
            raw_feature_names = [f"Feature_{i}" for i in range(X_trans.shape[1])]

        # Cache explainer instance by classifier id
        classifier_id = id(classifier)
        if classifier_id not in _SHAP_EXPLAINER_CACHE:
            try:
                # TreeExplainer is optimal for XGBoost, Random Forest, Gradient Boosting, Decision Tree
                explainer = shap.TreeExplainer(classifier)
            except Exception:
                try:
                    explainer = shap.TreeExplainer(classifier, feature_perturbation="tree_path_dependent")
                except Exception:
                    explainer = shap.Explainer(getattr(classifier, "predict_proba", classifier))
            _SHAP_EXPLAINER_CACHE[classifier_id] = explainer
        else:
            explainer = _SHAP_EXPLAINER_CACHE[classifier_id]

        # Calculate SHAP values
        try:
            shap_values = explainer.shap_values(X_trans)
        except Exception:
            shap_obj = explainer(X_trans)
            shap_values = shap_obj.values

        # Handle different SHAP output formats across models
        # For multi-class, shape can be (n_samples, n_features, n_classes) or list of arrays
        if isinstance(shap_values, list):
            # List of arrays [class_0, class_1, class_2]
            class_shap = shap_values[predicted_class_idx][0]
        elif len(shap_values.shape) == 3:
            # Array of shape (1, n_features, n_classes)
            class_shap = shap_values[0, :, predicted_class_idx]
        elif len(shap_values.shape) == 2:
            class_shap = shap_values[0]
        else:
            class_shap = np.array(shap_values).flatten()

        # Map individual features
        individual_attributions = []
        for feat_name, val in zip(raw_feature_names, class_shap):
            clean_name = get_clean_feature_name(feat_name)
            individual_attributions.append({
                "raw_name": feat_name,
                "feature": clean_name,
                "shap_value": round(float(val), 4),
                "direction": "Pushes towards risk" if val > 0 else "Protective buffer"
            })

        # Aggregate SHAP values into high-level GROUPS for direct comparison with Occlusion
        group_shap: Dict[str, float] = {g: 0.0 for g in GROUPS}
        for item in individual_attributions:
            fname = item["raw_name"].lower()
            matched = False
            for gname, cols in GROUPS.items():
                for c in cols:
                    if f"__{c}" in fname or f"_{c}_" in fname:
                        group_shap[gname] += item["shap_value"]
                        matched = True
                        break
                if matched:
                    break
            if not matched and "bmi" in fname:
                group_shap["BMI (Height & Weight)"] += item["shap_value"]

        total_group_abs = sum(abs(v) for v in group_shap.values()) or 1.0
        grouped_list = [
            {
                "name": gname,
                "shap_value": round(val, 4),
                "share": round(100.0 * abs(val) / total_group_abs, 1),
                "direction": "Pushes toward risk" if val > 0 else "Protective buffer",
                "arrow": "▲" if val > 0 else "▼"
            }
            for gname, val in group_shap.items()
        ]
        grouped_list.sort(key=lambda x: -x["share"])

        # Top positive and negative individual contributors
        sorted_indiv = sorted(individual_attributions, key=lambda x: x["shap_value"], reverse=True)
        top_positive = [f for f in sorted_indiv if f["shap_value"] > 0][:5]
        top_negative = [f for f in sorted_indiv if f["shap_value"] < 0][::-1][:5]

        return {
            "method": "SHAP (TreeExplainer)",
            "available": True,
            "grouped_attributions": grouped_list,
            "individual_attributions": sorted_indiv,
            "top_risk_drivers": top_positive,
            "top_protective": top_negative,
            "baseline_value": getattr(explainer, "expected_value", None)
        }

    except Exception as exc:
        logger.warning("SHAP calculation encountered error (%s); falling back to Occlusion.", exc)
        return {
            "method": "SHAP",
            "available": False,
            "error": str(exc)
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Methodology & Limitations Documentation Metadata
# ─────────────────────────────────────────────────────────────────────────────

XAI_METHODOLOGY_INFO = {
    "occlusion": {
        "title": "Occlusion-Based Sensitivity Analysis",
        "badge": "Primary XAI Method",
        "description": (
            "Occlusion sensitivity calculates the local change in predicted risk probability (ΔP) "
            "when an individual's specific attribute group is replaced by the population reference "
            "value (median for numerical variables, mode for categorical variables). "
            "A positive ΔP indicates that the individual's value is actively driving the model toward "
            "the predicted risk classification."
        ),
        "limitations": [
            "Evaluates localized marginal changes; does not measure complex higher-order feature interactions.",
            "Assumes independence during baseline replacement (perturbation space).",
            "Baseline reference values reflect the current dataset's cohort medians and modes."
        ]
    },
    "shap": {
        "title": "SHAP (SHapley Additive exPlanations)",
        "badge": "Optional Advanced Game-Theoretic XAI",
        "description": (
            "SHAP computes fair Shapley values derived from cooperative game theory. "
            "It measures the marginal contribution of each feature to the model's raw prediction margin "
            "across all possible combinatorial coalitions of features."
        ),
        "limitations": [
            "TreeExplainer evaluates attributions in the model's log-odds / margin space prior to softmax normalization.",
            "One-hot encoded categories are computed individually and mapped back to feature groups.",
            "Computationally more intensive than occlusion sensitivity."
        ]
    }
}
