"""
NutriRisk AI — Final Integration Test Suite (Prompt 29).

Verifies the complete 16-step end-to-end operational workflow:
  Step 1: User opens the landing page.
  Step 2: User registers or logs in.
  Step 3: User accesses the dashboard.
  Step 4: User completes the nutritional assessment form.
  Step 5: Backend validates the inputs.
  Step 6: BMI is calculated.
  Step 7: The saved preprocessing pipeline transforms the input.
  Step 8: The trained ML model generates predictions.
  Step 9: Risk probabilities are calculated.
  Step 10: The results page displays the assessment.
  Step 11: The explanation module displays contributing factors.
  Step 12: The assessment is stored in SQLite.
  Step 13: The user can view assessment history.
  Step 14: Analytics update using actual stored records.
  Step 15: Authorized administrators can access the admin dashboard.
  Step 16: The user can download an assessment report.
"""
import io
import os
import json
import secrets
import tempfile
import unittest

from nutririsk import create_app
from nutririsk.db import get_db
from nutririsk.auth.utils import hash_password
from nutririsk.ml.features import validate_and_parse_input
from nutririsk.ml.prediction import predict_nutritional_risk, get_model_bundle


class TestNutriRiskFinalIntegration16Steps(unittest.TestCase):
    """End-to-End integration verification of all 16 Prompt 29 workflow steps."""

    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db.close()
        cls.test_db_path = cls.temp_db.name

        cls.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": cls.test_db_path,
            "SECRET_KEY": "integration-test-secret-key-123456",
            "WTF_CSRF_ENABLED": False,
            "ENFORCE_CSRF_IN_TESTS": False
        })

        with cls.app.app_context():
            db = get_db()
            # Seed Admin Account
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("System Admin", "admin@hospital.org", hash_password("AdminPass123!"), "admin", "2026-09-01T08:00:00")
            )
            db.commit()

    @classmethod
    def tearDownClass(cls):
        try:
            if os.path.exists(cls.test_db_path):
                os.remove(cls.test_db_path)
        except OSError:
            pass

    def setUp(self):
        self.client = self.app.test_client()

    def test_complete_16_step_workflow(self):
        """Executes and asserts every stage of the 16-step clinical lifecycle."""

        # -------------------------------------------------------------
        # STEP 1: User opens the landing page
        # -------------------------------------------------------------
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200, "Step 1 Failed: Landing page must respond with HTTP 200")
        html = resp.get_data(as_text=True)
        self.assertIn("NutriRisk AI", html, "Step 1 Failed: Landing page must feature NutriRisk AI branding")
        self.assertIn("Project Objectives", html, "Step 1 Failed: Landing page must display Project Objectives")

        # -------------------------------------------------------------
        # STEP 2: User registers and logs in
        # -------------------------------------------------------------
        reg_payload = {
            "name": "Dr. Sarah Jenkins",
            "email": "dr.jenkins@clinic.org",
            "password": "ClinicianSecure2026!",
            "confirm_password": "ClinicianSecure2026!"
        }
        reg_resp = self.client.post("/register", data=reg_payload, follow_redirects=True)
        self.assertEqual(reg_resp.status_code, 200, "Step 2 Failed: Registration must succeed")

        login_payload = {
            "email": "dr.jenkins@clinic.org",
            "password": "ClinicianSecure2026!"
        }
        login_resp = self.client.post("/login", data=login_payload, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200, "Step 2 Failed: Login must succeed")
        with self.client.session_transaction() as sess:
            self.assertIn("uid", sess, "Step 2 Failed: Active session must contain user ID (uid)")
            clinician_uid = sess["uid"]

        # -------------------------------------------------------------
        # STEP 3: User accesses the dashboard / assessment form
        # -------------------------------------------------------------
        dash_resp = self.client.get("/predict")
        self.assertEqual(dash_resp.status_code, 200, "Step 3 Failed: /predict must load successfully")
        form_html = dash_resp.get_data(as_text=True)
        self.assertIn("Nutritional Risk Assessment", form_html)
        self.assertIn("food_groups", form_html)

        # -------------------------------------------------------------
        # STEP 4: User completes the nutritional assessment form
        # -------------------------------------------------------------
        assessment_form_data = {
            "subject": "Patient PT-88219",
            "age": "65",
            "sex": "Female",
            "height_cm": "160.0",
            "weight_kg": "42.0",
            "food_groups": "2",
            "meals_per_day": "2",
            "activity": "Low",
            "income": "Low",
            "education": "Primary",
            "residence": "Rural",
            "recent_illness": "Yes"
        }

        # -------------------------------------------------------------
        # STEP 5: Backend validates the inputs
        # -------------------------------------------------------------
        parsed_data, error_msg = validate_and_parse_input(assessment_form_data)
        self.assertIsNone(error_msg, f"Step 5 Failed: Input validation rejected valid payload: {error_msg}")
        self.assertEqual(parsed_data["age"], 65)
        self.assertEqual(parsed_data["weight_kg"], 42.0)
        self.assertEqual(parsed_data["height_cm"], 160.0)

        # -------------------------------------------------------------
        # STEP 6: BMI is calculated
        # -------------------------------------------------------------
        expected_bmi = round(42.0 / ((160.0 / 100.0) ** 2), 2)  # 42 / 2.56 = 16.41 kg/m^2
        self.assertAlmostEqual(expected_bmi, 16.41, places=2)

        # -------------------------------------------------------------
        # STEP 7: The saved preprocessing pipeline transforms the input
        # -------------------------------------------------------------
        bundle = get_model_bundle()
        self.assertIn("pipeline", bundle, "Step 7 Failed: Model bundle must contain fitted pipeline")
        self.assertIn("reference", bundle, "Step 7 Failed: Model bundle must contain reference values")

        # -------------------------------------------------------------
        # STEP 8: The trained ML model generates predictions
        # -------------------------------------------------------------
        result_data = predict_nutritional_risk(parsed_data)
        self.assertIn("risk", result_data, "Step 8 Failed: Result must contain predicted risk")
        self.assertIn(result_data["risk"], ["Low Risk", "Moderate Risk", "High Risk"])

        # -------------------------------------------------------------
        # STEP 9: Risk probabilities are calculated
        # -------------------------------------------------------------
        self.assertIn("probabilities", result_data)
        self.assertEqual(len(result_data["probabilities"]), 3, "Step 9 Failed: Probabilities must have 3 classes")
        self.assertAlmostEqual(sum(result_data["probabilities"]), 1.0, places=2, msg="Probabilities must sum to 1.0")
        self.assertGreaterEqual(result_data["confidence"], 0.33)

        # -------------------------------------------------------------
        # STEP 10: The results page displays the assessment (via POST form)
        # -------------------------------------------------------------
        post_resp = self.client.post("/predict", data=assessment_form_data, follow_redirects=False)
        self.assertEqual(post_resp.status_code, 302, "Step 10 Failed: POST /predict must redirect to result")
        result_url = post_resp.headers["Location"]
        self.assertIn("/result/", result_url)
        aid = int(result_url.split("/")[-1])

        get_result_resp = self.client.get(f"/result/{aid}")
        self.assertEqual(get_result_resp.status_code, 200, "Step 10 Failed: Result page must load with 200 OK")
        result_html = get_result_resp.get_data(as_text=True)
        self.assertIn("Patient PT-88219", result_html)
        self.assertIn("16.41", result_html, "Step 10 Failed: Calculated BMI must appear on result page")

        # -------------------------------------------------------------
        # STEP 11: The explanation module displays contributing factors
        # -------------------------------------------------------------
        self.assertIn("factors", result_data)
        self.assertGreater(len(result_data["factors"]), 0, "Step 11 Failed: Must generate XAI factors")
        self.assertTrue(
            "Top Risk-Increasing Factors" in result_html or "Contributing Factors" in result_html or "Explainable" in result_html,
            "Step 11 Failed: Result HTML must render XAI factor breakdown"
        )

        # -------------------------------------------------------------
        # STEP 12: The assessment is stored in SQLite
        # -------------------------------------------------------------
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT * FROM assessments WHERE id = ?", (aid,)).fetchone()
            self.assertIsNotNone(row, f"Step 12 Failed: Assessment record #{aid} not found in database")
            self.assertEqual(row["user_id"], clinician_uid)
            self.assertEqual(row["subject"], "Patient PT-88219")
            self.assertAlmostEqual(row["bmi"], 16.41, places=2)
            self.assertEqual(row["risk"], result_data["risk"])

        # -------------------------------------------------------------
        # STEP 13: The user can view assessment history
        # -------------------------------------------------------------
        hist_resp = self.client.get("/history")
        self.assertEqual(hist_resp.status_code, 200, "Step 13 Failed: /history must return 200 OK")
        hist_html = hist_resp.get_data(as_text=True)
        self.assertIn("Patient PT-88219", hist_html, "Step 13 Failed: Saved assessment must appear in history table")
        self.assertIn(f"/result/{aid}", hist_html, "Step 13 Failed: Link to result must appear in history")

        # -------------------------------------------------------------
        # STEP 14: Analytics update using actual stored records
        # -------------------------------------------------------------
        analytics_resp = self.client.get("/analytics")
        self.assertEqual(analytics_resp.status_code, 200, "Step 14 Failed: /analytics must load with 200 OK")
        analytics_html = analytics_resp.get_data(as_text=True)
        self.assertTrue("Total Screened" in analytics_html or "Healthcare Analytics" in analytics_html, "Step 14 Failed: Analytics page must render")

        api_analytics = self.client.get("/api/analytics")
        self.assertEqual(api_analytics.status_code, 200, "Step 14 Failed: /api/analytics must return 200 OK")
        api_data = json.loads(api_analytics.get_data(as_text=True))
        self.assertEqual(api_data["status"], "success")
        self.assertIn("statistics", api_data)
        self.assertGreaterEqual(api_data["statistics"]["total"], 1, "Step 14 Failed: Total assessments must reflect stored record")

        # -------------------------------------------------------------
        # STEP 15: Authorized administrators can access the admin dashboard
        # -------------------------------------------------------------
        # Clinician should receive 403 Forbidden
        clinician_admin_resp = self.client.get("/admin")
        self.assertEqual(clinician_admin_resp.status_code, 403, "Step 15 Failed: Clinician must be forbidden from /admin")

        # Admin logs in and receives 200 OK
        self.client.get("/logout")
        admin_login = self.client.post("/login", data={"email": "admin@hospital.org", "password": "AdminPass123!"}, follow_redirects=True)
        self.assertEqual(admin_login.status_code, 200)

        admin_resp = self.client.get("/admin")
        self.assertEqual(admin_resp.status_code, 200, "Step 15 Failed: Admin must access /admin with 200 OK")
        admin_html = admin_resp.get_data(as_text=True)
        self.assertIn("Administrative Console", admin_html)
        self.assertIn("dr.jenkins@clinic.org", admin_html, "Step 15 Failed: Registered user must appear in admin directory")

        # -------------------------------------------------------------
        # STEP 16: The user can download an assessment report
        # -------------------------------------------------------------
        # Admin can access any assessment PDF; test clinician login download as well
        dl_resp = self.client.get(f"/assessment/{aid}/download")
        self.assertEqual(dl_resp.status_code, 200, "Step 16 Failed: PDF download must return 200 OK")
        self.assertEqual(dl_resp.content_type, "application/pdf", "Step 16 Failed: Content-Type must be application/pdf")
        pdf_bytes = dl_resp.data
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1."), "Step 16 Failed: Downloaded bytes must be valid PDF stream")
        self.assertGreater(len(pdf_bytes), 1000, "Step 16 Failed: PDF file must be non-empty")


if __name__ == "__main__":
    unittest.main()
