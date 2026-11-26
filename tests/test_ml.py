"""
ML Unit Tests for NutriRisk AI — Prompt 10.

Tests cover:
  - BMI edge cases (boundary heights/weights)
  - Class probability mapping (sum ≈ 1.0, correct LABELS ordering)
  - Graceful handling of missing model artifact
  - Invalid input rejection (out-of-range, wrong types)
  - High-risk frail elder profile
  - Low-risk healthy adult profile
  - Dataset validation module

All tests are standalone and do not require a running Flask application.
"""
import os
import sys
import unittest
import tempfile
import pandas as pd
import numpy as np

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nutririsk.config import Config
from nutririsk.ml.features import (
    add_features, validate_and_parse_input, LABELS, RAW, GROUPS, CHOICES, VALIDATION_BOUNDS
)
from nutririsk.ml.prediction import predict_nutritional_risk


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────
def _make_payload(**overrides) -> dict:
    """Return a valid string-valued form payload with optional overrides."""
    base = {
        "age": "30", "sex": "Female", "height_cm": "165", "weight_kg": "60",
        "food_groups": "5", "meals_per_day": "3", "activity": "Moderate",
        "income": "Middle", "education": "Secondary", "residence": "Urban",
        "recent_illness": "No",
    }
    base.update({k: str(v) for k, v in overrides.items()})
    return base


def _make_input(**overrides) -> dict:
    """Return a valid parsed (typed) dict for predict_nutritional_risk."""
    base = {
        "age": 30, "sex": "Female", "height_cm": 165.0, "weight_kg": 60.0,
        "food_groups": 5, "meals_per_day": 3, "activity": "Moderate",
        "income": "Middle", "education": "Secondary", "residence": "Urban",
        "recent_illness": "No",
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# BMI feature engineering
# ─────────────────────────────────────────────────────────────────────────────
class TestBMIEngineering(unittest.TestCase):

    def test_bmi_standard(self):
        """BMI = weight / (height/100)^2, reference case."""
        df = pd.DataFrame([_make_input(height_cm=180.0, weight_kg=81.0)])
        out = add_features(df[RAW])
        self.assertIn("bmi", out.columns)
        # 81 / 1.8^2 = 25.0
        self.assertAlmostEqual(out["bmi"].iloc[0], 25.0, places=1)

    def test_bmi_underweight_boundary(self):
        """Minimum valid height/weight combination should still produce finite BMI."""
        df = pd.DataFrame([_make_input(height_cm=120.0, weight_kg=25.0)])
        out = add_features(df[RAW])
        bmi = out["bmi"].iloc[0]
        self.assertTrue(np.isfinite(bmi), f"BMI is not finite: {bmi}")
        # 25 / 1.2^2 ≈ 17.36
        self.assertAlmostEqual(bmi, 25.0 / (1.2 ** 2), places=1)

    def test_bmi_obese_boundary(self):
        """Maximum valid height/weight combination should still produce finite BMI."""
        df = pd.DataFrame([_make_input(height_cm=220.0, weight_kg=250.0)])
        out = add_features(df[RAW])
        bmi = out["bmi"].iloc[0]
        self.assertTrue(np.isfinite(bmi), f"BMI is not finite: {bmi}")
        # 250 / 2.2^2 ≈ 51.65
        self.assertGreater(bmi, 40.0)

    def test_bmi_near_zero_height_clipped(self):
        """Height is clipped to ≥50 cm internally to prevent ZeroDivisionError."""
        df = pd.DataFrame([_make_input(height_cm=0.0, weight_kg=50.0)])
        out = add_features(df[RAW])
        bmi = out["bmi"].iloc[0]
        # Should not raise; result should be finite (clipping prevents ÷0)
        self.assertTrue(np.isfinite(bmi))

    def test_bmi_column_present_after_add_features(self):
        """add_features() always adds 'bmi' column regardless of input data."""
        df = pd.DataFrame([_make_input()])
        out = add_features(df[RAW])
        self.assertIn("bmi", out.columns)
        self.assertEqual(len(out), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Input validation
# ─────────────────────────────────────────────────────────────────────────────
class TestInputValidation(unittest.TestCase):

    def test_valid_input_passes(self):
        """A fully valid payload passes schema validation."""
        data, err = validate_and_parse_input(_make_payload())
        self.assertIsNone(err)
        self.assertIsNotNone(data)
        self.assertEqual(data["age"], 30)
        self.assertEqual(data["sex"], "Female")

    def test_underage_rejected(self):
        """Age < 18 must be rejected (adult scope enforcement)."""
        _, err = validate_and_parse_input(_make_payload(age=15))
        self.assertIsNotNone(err)
        self.assertIn("18", err)

    def test_age_too_high_rejected(self):
        """Age > 100 must be rejected."""
        _, err = validate_and_parse_input(_make_payload(age=101))
        self.assertIsNotNone(err)

    def test_height_too_low_rejected(self):
        """Height below 120 cm must be rejected."""
        _, err = validate_and_parse_input(_make_payload(height_cm=100))
        self.assertIsNotNone(err)

    def test_height_too_high_rejected(self):
        """Height above 220 cm must be rejected."""
        _, err = validate_and_parse_input(_make_payload(height_cm=230))
        self.assertIsNotNone(err)

    def test_weight_too_low_rejected(self):
        """Weight below 25 kg must be rejected."""
        _, err = validate_and_parse_input(_make_payload(weight_kg=20))
        self.assertIsNotNone(err)

    def test_weight_too_high_rejected(self):
        """Weight above 250 kg must be rejected."""
        _, err = validate_and_parse_input(_make_payload(weight_kg=300))
        self.assertIsNotNone(err)

    def test_food_groups_zero_rejected(self):
        """Food groups = 0 must be rejected (min is 1)."""
        _, err = validate_and_parse_input(_make_payload(food_groups=0))
        self.assertIsNotNone(err)

    def test_food_groups_nine_rejected(self):
        """Food groups = 9 must be rejected (max is 8)."""
        _, err = validate_and_parse_input(_make_payload(food_groups=9))
        self.assertIsNotNone(err)

    def test_invalid_sex_rejected(self):
        """An unknown sex value must be rejected."""
        _, err = validate_and_parse_input(_make_payload(sex="Unknown"))
        self.assertIsNotNone(err)
        self.assertIn("sex", err.lower())

    def test_invalid_activity_rejected(self):
        """An invalid activity level must be rejected."""
        _, err = validate_and_parse_input(_make_payload(activity="Extreme"))
        self.assertIsNotNone(err)

    def test_invalid_income_rejected(self):
        """An invalid income level must be rejected."""
        _, err = validate_and_parse_input(_make_payload(income="VeryRich"))
        self.assertIsNotNone(err)

    def test_non_numeric_age_rejected(self):
        """Non-numeric age string must be rejected gracefully."""
        _, err = validate_and_parse_input(_make_payload(age="abc"))
        self.assertIsNotNone(err)

    def test_boundary_age_18_accepted(self):
        """Age = 18 (lower boundary) must be accepted."""
        data, err = validate_and_parse_input(_make_payload(age=18))
        self.assertIsNone(err)
        self.assertEqual(data["age"], 18)

    def test_boundary_age_100_accepted(self):
        """Age = 100 (upper boundary) must be accepted."""
        data, err = validate_and_parse_input(_make_payload(age=100))
        self.assertIsNone(err)
        self.assertEqual(data["age"], 100)


# ─────────────────────────────────────────────────────────────────────────────
# Class probability mapping
# ─────────────────────────────────────────────────────────────────────────────
class TestProbabilityMapping(unittest.TestCase):

    def test_probabilities_sum_to_one(self):
        """Class probabilities must sum to approximately 1.0."""
        res = predict_nutritional_risk(_make_input())
        prob_sum = sum(res["probabilities"])
        self.assertAlmostEqual(prob_sum, 1.0, places=3,
                               msg=f"Probabilities sum to {prob_sum}, expected ≈ 1.0")

    def test_probabilities_count_matches_labels(self):
        """Number of probability values must equal number of risk classes."""
        res = predict_nutritional_risk(_make_input())
        self.assertEqual(len(res["probabilities"]), len(LABELS))

    def test_probabilities_all_non_negative(self):
        """All class probabilities must be ≥ 0."""
        res = predict_nutritional_risk(_make_input())
        for i, p in enumerate(res["probabilities"]):
            self.assertGreaterEqual(p, 0.0, f"Probability[{i}] = {p} is negative")

    def test_predicted_class_has_highest_probability(self):
        """The predicted risk label must correspond to the argmax of probabilities."""
        res = predict_nutritional_risk(_make_input())
        predicted_idx = LABELS.index(res["risk"])
        max_prob_idx = int(np.argmax(res["probabilities"]))
        self.assertEqual(predicted_idx, max_prob_idx,
                         f"Predicted class index {predicted_idx} ≠ argmax index {max_prob_idx}")

    def test_confidence_matches_max_probability(self):
        """Confidence must equal the maximum class probability."""
        res = predict_nutritional_risk(_make_input())
        self.assertAlmostEqual(
            res["confidence"], max(res["probabilities"]), places=4,
            msg="Confidence does not match max probability."
        )

    def test_class_probabilities_dict_mapping(self):
        """class_probabilities maps every label in LABELS to a valid probability."""
        res = predict_nutritional_risk(_make_input())
        self.assertIn("class_probabilities", res)
        self.assertEqual(set(res["class_probabilities"].keys()), set(LABELS))
        for label, prob in res["class_probabilities"].items():
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Model not found & error handling
# ─────────────────────────────────────────────────────────────────────────────
class TestMissingModelArtifact(unittest.TestCase):

    def test_missing_model_raises_file_not_found(self):
        """When model file is absent, a FileNotFoundError with clear message is raised."""
        with self.assertRaises(FileNotFoundError) as ctx:
            predict_nutritional_risk(
                _make_input(),
                model_path=os.path.join(Config.BASE_DIR, "model", "nonexistent_model.joblib")
            )
        self.assertIn("model", str(ctx.exception).lower())

    def test_incomplete_input_raises_value_error(self):
        """When required features are missing from input_data, ValueError is raised."""
        incomplete = {"age": 30, "sex": "Female"}  # missing remaining fields
        with self.assertRaises(ValueError) as ctx:
            predict_nutritional_risk(incomplete)
        self.assertIn("Missing required feature", str(ctx.exception))


# ─────────────────────────────────────────────────────────────────────────────
# Prediction profiles
# ─────────────────────────────────────────────────────────────────────────────
class TestPredictionProfiles(unittest.TestCase):

    def test_model_returns_required_keys(self):
        """Prediction result must contain all expected keys."""
        res = predict_nutritional_risk(_make_input())
        for key in ("risk", "confidence", "probabilities", "factors", "bmi"):
            self.assertIn(key, res, f"Missing key: '{key}'")

    def test_risk_label_is_valid(self):
        """Predicted risk label must be one of the 3 defined categories."""
        res = predict_nutritional_risk(_make_input())
        self.assertIn(res["risk"], LABELS)

    def test_bmi_returned_correctly(self):
        """BMI in result must be a positive finite float."""
        res = predict_nutritional_risk(_make_input(height_cm=165.0, weight_kg=60.0))
        self.assertIsInstance(res["bmi"], float)
        self.assertGreater(res["bmi"], 0)
        self.assertTrue(np.isfinite(res["bmi"]))

    def test_factors_list_not_empty(self):
        """Explainability factors must be a non-empty list."""
        res = predict_nutritional_risk(_make_input())
        self.assertIsInstance(res["factors"], list)
        self.assertGreater(len(res["factors"]), 0)

    def test_frail_elder_high_risk(self):
        """Frail elder profile should produce High Risk with confidence > 0.50.

        Profile: elderly female, very low BMI, minimal diet, low activity,
        low income, no education, rural, recent illness.
        NOTE: With synthetic training data this test verifies the pipeline
        end-to-end, not clinical accuracy.
        """
        frail = _make_input(
            age=80, sex="Female", height_cm=150.0, weight_kg=35.0,
            food_groups=1, meals_per_day=1, activity="Low",
            income="Low", education="None", residence="Rural", recent_illness="Yes"
        )
        res = predict_nutritional_risk(frail)
        # Must return a valid label
        self.assertIn(res["risk"], LABELS)
        # On synthetic data trained with matching score formula, this should be High Risk
        self.assertEqual(
            res["risk"], "High Risk",
            f"Expected High Risk for frail elder profile, got: {res['risk']} "
            f"(confidence={res['confidence']:.3f}). "
            "If you replaced the synthetic dataset, update this assertion to match "
            "the new labeling methodology."
        )
        self.assertGreater(res["confidence"], 0.50)

    def test_healthy_young_adult_low_risk(self):
        """Healthy young adult profile should produce Low Risk.

        Profile: young male, healthy BMI, diverse diet, high activity,
        high income, higher education, urban, no recent illness.
        NOTE: With synthetic training data this test verifies the pipeline
        end-to-end, not clinical accuracy.
        """
        healthy = _make_input(
            age=25, sex="Male", height_cm=178.0, weight_kg=72.0,
            food_groups=8, meals_per_day=4, activity="High",
            income="High", education="Higher", residence="Urban", recent_illness="No"
        )
        res = predict_nutritional_risk(healthy)
        self.assertIn(res["risk"], LABELS)
        self.assertEqual(
            res["risk"], "Low Risk",
            f"Expected Low Risk for healthy young adult, got: {res['risk']} "
            f"(confidence={res['confidence']:.3f}). "
            "If you replaced the synthetic dataset, update this assertion to match "
            "the new labeling methodology."
        )
        self.assertGreater(res["confidence"], 0.40)

    def test_all_boundary_ages_accepted(self):
        """Predictions must complete without error for boundary ages (18 and 100)."""
        for age in (18, 100):
            with self.subTest(age=age):
                res = predict_nutritional_risk(_make_input(age=age))
                self.assertIn(res["risk"], LABELS)


# ─────────────────────────────────────────────────────────────────────────────
# Dataset validation module
# ─────────────────────────────────────────────────────────────────────────────
class TestDatasetValidation(unittest.TestCase):

    def _make_valid_df(self, n: int = 50) -> pd.DataFrame:
        """Create a minimal valid DataFrame for validation tests."""
        rng = np.random.default_rng(0)
        df = pd.DataFrame({
            "age": rng.integers(18, 80, n),
            "sex": rng.choice(["Female", "Male"], n),
            "height_cm": rng.uniform(140.0, 200.0, n).round(1),
            "weight_kg": rng.uniform(40.0, 120.0, n).round(1),
            "food_groups": rng.integers(1, 9, n),
            "meals_per_day": rng.integers(1, 6, n),
            "activity": rng.choice(["Low", "Moderate", "High"], n),
            "income": rng.choice(["Low", "Middle", "High"], n),
            "education": rng.choice(["None", "Primary", "Secondary", "Higher"], n),
            "residence": rng.choice(["Urban", "Rural"], n),
            "recent_illness": rng.choice(["No", "Yes"], n),
            "risk": rng.choice(["Low Risk", "Moderate Risk", "High Risk"], n),
        })
        return df

    def test_valid_schema_passes(self):
        """A correctly structured DataFrame passes schema validation."""
        from nutririsk.ml.data_validation import validate_dataset_schema
        df = self._make_valid_df()
        try:
            validate_dataset_schema(df)
        except Exception as e:
            self.fail(f"validate_dataset_schema raised unexpectedly: {e}")

    def test_missing_risk_column_raises(self):
        """DataFrame without 'risk' column raises DatasetValidationError."""
        from nutririsk.ml.data_validation import validate_dataset_schema, DatasetValidationError
        df = self._make_valid_df().drop(columns=["risk"])
        with self.assertRaises(DatasetValidationError):
            validate_dataset_schema(df)

    def test_missing_feature_column_raises(self):
        """DataFrame missing a RAW feature column raises DatasetValidationError."""
        from nutririsk.ml.data_validation import validate_dataset_schema, DatasetValidationError
        df = self._make_valid_df().drop(columns=["age"])
        with self.assertRaises(DatasetValidationError):
            validate_dataset_schema(df)

    def test_quality_report_structure(self):
        """generate_data_quality_report returns a dict with all expected sections."""
        from nutririsk.ml.data_validation import generate_data_quality_report
        df = self._make_valid_df()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
            import json
            json.dump({"is_real_data": False, "source": "test"}, tmp)
            tmp_path = tmp.name
        try:
            report = generate_data_quality_report(df, metadata_path=tmp_path)
            for section in ("schema", "missing_values", "duplicates",
                            "value_ranges", "class_distribution",
                            "adult_scope", "provenance", "leakage", "summary"):
                self.assertIn(section, report, f"Missing section: '{section}'")
        finally:
            os.unlink(tmp_path)

    def test_minor_detection(self):
        """check_adult_scope correctly counts rows with age < 18."""
        from nutririsk.ml.data_validation import check_adult_scope
        df = self._make_valid_df(50)
        df.at[0, "age"] = 10  # Inject a minor
        df.at[1, "age"] = 16
        result = check_adult_scope(df)
        self.assertGreaterEqual(result["minors_found"], 2)

    def test_invalid_categorical_detected(self):
        """check_categorical_values flags values outside CHOICES domains."""
        from nutririsk.ml.data_validation import check_categorical_values
        df = self._make_valid_df(50)
        df.at[0, "sex"] = "Other"
        result = check_categorical_values(df)
        self.assertGreater(result["sex"]["violation_count"], 0)

    def test_duplicate_detection(self):
        """check_duplicates correctly identifies duplicated rows."""
        from nutririsk.ml.data_validation import check_duplicates
        df = self._make_valid_df(20)
        df_dup = pd.concat([df, df.iloc[:5]], ignore_index=True)
        result = check_duplicates(df_dup)
        self.assertEqual(result["duplicate_rows"], 5)

    def test_class_distribution_all_labels_present(self):
        """check_class_distribution returns counts for all three LABELS."""
        from nutririsk.ml.data_validation import check_class_distribution
        df = self._make_valid_df(300)
        result = check_class_distribution(df)
        for label in LABELS:
            self.assertIn(label, result)


# ─────────────────────────────────────────────────────────────────────────────
# Explainable AI (XAI) Tests — Prompt 11
# ─────────────────────────────────────────────────────────────────────────────
class TestExplainableAI(unittest.TestCase):

    def test_occlusion_factor_structure_and_explanations(self):
        """Verifies that occlusion attributions include effects, shares, arrows, and narrative text."""
        from nutririsk.ml.prediction import get_model_bundle
        from nutririsk.ml.explainability import compute_occlusion_attributions
        bundle = get_model_bundle()
        input_data = _make_input(age=78, weight_kg=38.0, height_cm=152.0, food_groups=2, recent_illness="Yes")
        factors = compute_occlusion_attributions(
            pipeline=bundle["pipeline"],
            reference_values=bundle["reference"],
            input_dict=input_data,
            predicted_class_idx=2,  # High Risk
            predicted_prob=0.85
        )
        self.assertIsInstance(factors, list)
        self.assertEqual(len(factors), len(GROUPS))
        total_share = sum(f["share"] for f in factors)
        self.assertAlmostEqual(total_share, 100.0, delta=1.5)

        for factor in factors:
            self.assertIn("name", factor)
            self.assertIn("effect", factor)
            self.assertIn("share", factor)
            self.assertIn("direction", factor)
            self.assertIn(factor["arrow"], ("▲", "▼"))
            self.assertIn("explanation", factor)
            self.assertIsInstance(factor["explanation"], str)
            self.assertGreater(len(factor["explanation"]), 15)

    def test_shap_attributions_when_available(self):
        """Tests that compute_shap_attributions generates grouped and individual Shapley values."""
        from nutririsk.ml.prediction import get_model_bundle
        from nutririsk.ml.explainability import compute_shap_attributions
        bundle = get_model_bundle()
        input_data = _make_input(age=28, weight_kg=70.0, height_cm=175.0, food_groups=7, activity="High")
        shap_res = compute_shap_attributions(
            pipeline=bundle["pipeline"],
            input_dict=input_data,
            predicted_class_idx=0  # Low Risk
        )
        self.assertIsNotNone(shap_res)
        self.assertTrue(shap_res["available"])
        self.assertIn("grouped_attributions", shap_res)
        self.assertIn("individual_attributions", shap_res)
        self.assertGreater(len(shap_res["grouped_attributions"]), 0)
        self.assertGreater(len(shap_res["individual_attributions"]), 0)

        # Check clean feature names
        sample_feature = shap_res["individual_attributions"][0]["feature"]
        self.assertNotIn("num__", sample_feature)
        self.assertNotIn("cat__", sample_feature)

    def test_xai_consistency_across_sample_profiles(self):
        """Verifies explanation consistency across distinct clinical/demographic profiles."""
        # 1. Frail elder (malnutrition archetype)
        frail = _make_input(age=82, weight_kg=36.0, height_cm=150.0, food_groups=1, meals_per_day=1, recent_illness="Yes")
        res_frail = predict_nutritional_risk(frail)
        top_factor_names = [f["name"] for f in res_frail["factors"][:3]]
        # BMI or Dietary Diversity or Age should be in the top drivers
        self.assertTrue(
            any(k in top_factor_names for k in ("BMI (Height & Weight)", "Dietary Diversity", "Age")),
            f"Expected key vulnerability in top 3 factors, got: {top_factor_names}"
        )

        # 2. Healthy robust young adult (low risk archetype)
        healthy = _make_input(age=24, weight_kg=68.0, height_cm=176.0, food_groups=8, meals_per_day=4, activity="High", income="High")
        res_healthy = predict_nutritional_risk(healthy)
        self.assertEqual(res_healthy["risk"], "Low Risk")
        self.assertGreater(len(res_healthy["factors"]), 0)


# ─────────────────────────────────────────────────────────────────────────────
# Original tests (preserved for regression)
# ─────────────────────────────────────────────────────────────────────────────
class TestMLComponents(unittest.TestCase):

    def test_bmi_feature_engineering(self):
        """Validates that BMI is computed accurately: weight / (height/100)^2."""
        df = pd.DataFrame([{
            "age": 25, "sex": "Male", "height_cm": 180.0, "weight_kg": 81.0,
            "food_groups": 6, "meals_per_day": 3, "activity": "High",
            "income": "High", "education": "Higher", "residence": "Urban", "recent_illness": "No"
        }])
        transformed = add_features(df)
        self.assertIn("bmi", transformed.columns)
        # 81 / (1.8^2) = 25.0
        self.assertAlmostEqual(transformed["bmi"].iloc[0], 25.0, places=1)

    def test_input_validation_valid(self):
        """Tests that a valid input payload passes schema validation."""
        valid_payload = {
            "age": "30", "sex": "Female", "height_cm": "165", "weight_kg": "60",
            "food_groups": "5", "meals_per_day": "3", "activity": "Moderate",
            "income": "Middle", "education": "Secondary", "residence": "Urban", "recent_illness": "No"
        }
        data, err = validate_and_parse_input(valid_payload)
        self.assertIsNone(err)
        self.assertEqual(data["age"], 30)
        self.assertEqual(data["sex"], "Female")

    def test_input_validation_underage(self):
        """Tests rejection of underage patients (Adult scope 18+)."""
        invalid_payload = {
            "age": "15", "sex": "Male", "height_cm": "160", "weight_kg": "50",
            "food_groups": "4", "meals_per_day": "3", "activity": "Low",
            "income": "Low", "education": "None", "residence": "Rural", "recent_illness": "No"
        }
        data, err = validate_and_parse_input(invalid_payload)
        self.assertIsNone(data)
        self.assertIn("Age must be between 18 and 100", err)

    def test_model_inference_pipeline(self):
        """Tests that prediction returns expected keys, probabilities, and factors."""
        sample_input = {
            "age": 75, "sex": "Female", "height_cm": 150.0, "weight_kg": 38.0,
            "food_groups": 2, "meals_per_day": 1, "activity": "Low",
            "income": "Low", "education": "None", "residence": "Rural", "recent_illness": "Yes"
        }
        res = predict_nutritional_risk(sample_input)
        self.assertIn("risk", res)
        self.assertIn(res["risk"], LABELS)
        self.assertIn("confidence", res)
        self.assertIn("probabilities", res)
        self.assertEqual(len(res["probabilities"]), 3)
        self.assertIn("factors", res)
        self.assertTrue(len(res["factors"]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
