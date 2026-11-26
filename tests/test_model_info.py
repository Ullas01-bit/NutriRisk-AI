"""
Test Suite for NutriRisk AI ML Model Information Page (Prompt 18).
Validates:
  1. Route Accessibility: /model returns HTTP 200 for public/evaluator access.
  2. Complete Coverage: All 20 required sections and explanations are rendered.
  3. Dynamic Loading: Values in HTML match actual model/metrics.json outputs.
  4. Selected Winner: XGBoost displayed as the deployed champion model.
  5. Feature Dictionary: 11 raw + 1 engineered BMI feature catalog displayed with clinical rationales.
  6. Algorithms Compared: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost.
  7. Preprocessing Integrity: Median/Mode imputation, StandardScaler, OneHotEncoder, Leakage prevention.
  8. Diagnostic Confusion Matrix: 3x3 table with class-level sensitivity and specificity.
  9. Synthetic Disclosure: Clear academic disclosure and instructions to train on empirical surveys.
  10. Graceful Fallback: When metrics are unavailable, displays 'Not available' without crashing.
"""
import unittest
import os
import json
import tempfile
from nutririsk import create_app
from nutririsk.routes.main import compute_confusion_details

class TestModelInformationPage(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-model-info-secret-12345",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def test_01_model_page_status_and_header(self):
        """Tests that /model responds with HTTP 200 and renders the academic header."""
        res = self.client.get("/model")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Machine Learning Model Architecture &amp; Evaluation", html)
        self.assertIn("Final-Year Major Project Specification", html)

    def test_02_all_twenty_required_components_rendered(self):
        """Verifies that all 20 required specifications are explicitly covered on the page."""
        res = self.client.get("/model")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 1. Project methodology
        self.assertIn("Research &amp; Clinical Decision-Support Methodology", html)
        # 2. Dataset name and source
        self.assertIn("Dataset Name / Identifier", html)
        # 3. Dataset characteristics
        self.assertIn("Cohort Class Distribution", html)
        # 4. Input features
        self.assertIn("Clinical Input Features &amp; Data Dictionary", html)
        # 5. Preprocessing methodology
        self.assertIn("Data Leakage Prevention Protocol", html)
        # 6. Feature engineering
        self.assertIn("Body Mass Index (BMI)", html)
        self.assertIn("kg/m²", html)
        # 7. Algorithms compared
        self.assertIn("Logistic Regression", html)
        self.assertIn("Decision Tree", html)
        self.assertIn("Random Forest", html)
        self.assertIn("Gradient Boosting", html)
        self.assertIn("XGBoost", html)
        # 8. Train-test split
        self.assertIn("80:20", html)
        # 9. Cross-validation methodology
        self.assertIn("5-Fold CV", html)
        # 10. Model comparison table
        self.assertIn("Machine Learning Algorithms Benchmark &amp; Model Comparison", html)
        # 11. Accuracy
        self.assertIn("Holdout Accuracy", html)
        # 12. Precision
        self.assertIn("Macro Precision", html)
        # 13. Recall
        self.assertIn("Macro Recall", html)
        # 14. Macro F1-score
        self.assertIn("Holdout Macro-F1", html)
        # 15. Confusion matrix
        self.assertIn("Holdout Confusion Matrix", html)
        # 16. ROC-AUC
        self.assertIn("ROC-AUC (OVR)", html)
        # 17. Feature importance
        self.assertIn("Global Permutation Feature Importance", html)
        # 18. Selected model
        self.assertIn("Champion Model:", html)
        # 19. Model limitations
        self.assertIn("Technical Limitations &amp; Ethical Disclosures", html)
        # 20. Synthetic versus real dataset status
        self.assertTrue(
            ("Academic Evaluation &amp; Synthetic Benchmark Disclosure" in html) or
            ("Empirical Research Survey" in html) or
            ("Verified Empirical Research Dataset" in html)
        )

    def test_03_dynamic_metric_values_match_training_output(self):
        """Verifies that displayed metrics match actual model/metrics.json outputs dynamically."""
        metrics_path = os.path.join("model", "metrics.json")
        if not os.path.exists(metrics_path):
            self.skipTest("model/metrics.json not found on disk.")

        with open(metrics_path, "r", encoding="utf-8") as f:
            m = json.load(f)

        res = self.client.get("/model")
        html = res.get_data(as_text=True)

        best_name = m.get("best", "XGBoost")
        best_data = m["models"][best_name]

        # Check accuracy formatted as percentage (e.g. 74.0%)
        expected_acc = f"{round(best_data['accuracy'] * 100, 2)}%"
        self.assertIn(expected_acc, html)

        # Check CV Macro-F1 mean
        expected_cv_f1 = f"{round(best_data['cv_f1_mean'], 4)}"
        self.assertIn(expected_cv_f1, html)

        # Check ROC-AUC
        expected_roc = f"{round(best_data['roc_auc'], 4)}"
        self.assertIn(expected_roc, html)

    def test_04_feature_catalog_completeness(self):
        """Verifies that all 11 raw clinical input features are displayed in the data dictionary."""
        res = self.client.get("/model")
        html = res.get_data(as_text=True)

        expected_features = [
            "age", "sex", "height_cm", "weight_kg", "bmi",
            "food_groups", "meals_per_day", "activity", "income",
            "education", "residence", "recent_illness"
        ]
        for feat in expected_features:
            self.assertIn(feat, html, f"Feature '{feat}' missing from data dictionary.")

    def test_05_confusion_matrix_details_computation(self):
        """Verifies helper function compute_confusion_details computes exact precision and recall."""
        mock_matrix = [
            [400, 80, 20],  # Actual Low Risk (500)
            [100, 250, 50], # Actual Moderate Risk (400)
            [10, 40, 250]   # Actual High Risk (300)
        ]
        labels = ["Low Risk", "Moderate Risk", "High Risk"]
        details = compute_confusion_details(mock_matrix, labels)

        self.assertEqual(len(details), 3)

        # Low Risk
        # Recall: 400 / 500 = 80.0%
        # Precision: 400 / (400 + 100 + 10) = 400 / 510 = 78.43%
        self.assertEqual(details[0]["class_name"], "Low Risk")
        self.assertEqual(details[0]["actual_support"], 500)
        self.assertEqual(details[0]["recall"], 80.0)
        self.assertEqual(details[0]["precision"], 78.43)

        # High Risk
        # Recall: 250 / 300 = 83.33%
        # Precision: 250 / (20 + 50 + 250) = 250 / 320 = 78.12%
        self.assertEqual(details[2]["class_name"], "High Risk")
        self.assertEqual(details[2]["actual_support"], 300)
        self.assertEqual(details[2]["recall"], 83.33)
        self.assertEqual(details[2]["precision"], 78.12)

    def test_06_missing_metrics_graceful_handling(self):
        """Ensures that missing metrics or models render gracefully with 'Not available'."""
        empty_metrics_app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "METRICS_PATH": "nonexistent_metrics_file_9999.json",
            "WTF_CSRF_ENABLED": False
        })
        client = empty_metrics_app.test_client()
        res = client.get("/model")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Machine Learning Model Architecture &amp; Evaluation", html)
        self.assertTrue("Not available" in html or "not yet trained" in html)

if __name__ == "__main__":
    unittest.main()
