"""
Test Suite for NutriRisk AI Downloadable Clinical PDF Reports (Prompt 19).
Validates:
  1. Access Control: Anonymous redirected to /login, non-owner receives 404.
  2. Owner Access: Authenticated owner can download valid PDF with correct headers.
  3. Admin Access: Administrator can download any user's PDF report.
  4. Nonexistent Record: Requesting non-existent assessment returns 404.
  5. File Integrity: PDF starts with %PDF-, has valid size, and uses standard A4 geometry (595.27 x 841.89 pt).
  6. Privacy Guarantee: Zero exposure of passwords, password hashes, or sensitive session data.
  7. Multi-Tier Compatibility: Successfully renders Low, Moderate, and High Risk profiles.
  8. Robustness: Gracefully handles malformed JSON strings or empty factor arrays.
"""
import unittest
import os
import json
import tempfile
from datetime import datetime
from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password
from nutririsk.pdf_report import generate_assessment_pdf

class TestDownloadablePDFReport(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-pdf-secret-key-12345",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # 1. Admin User (ID = 1)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Admin", "admin@hospital.org", hash_password("AdminSecurePass999!"), "admin", "2026-09-01T08:00:00")
            )
            # 2. Clinician 1 (ID = 2)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Clinician One", "user1@clinic.org", hash_password("UserOnePass888!"), "user", "2026-09-15T08:00:00")
            )
            # 3. Clinician 2 (ID = 3)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Clinician Two", "user2@clinic.org", hash_password("UserTwoPass777!"), "user", "2026-09-20T08:00:00")
            )
            db.commit()

            # Seed Assessment for Clinician 1 (ID = 1)
            self.aid_user1 = insert_assessment(
                db=db,
                user_id=2,
                subject="Patient Alice",
                inputs={
                    "age": 28, "sex": "Female", "height_cm": 165.0, "weight_kg": 58.0,
                    "food_groups": 6, "meals_per_day": 3, "activity": "Moderate",
                    "income": "High", "education": "Higher", "residence": "Urban", "recent_illness": "No"
                },
                risk="Low Risk",
                confidence=0.92,
                probabilities=[0.92, 0.07, 0.01],
                factors=[
                    {"name": "Dietary Diversity", "direction": "Protective (toward Low)", "share": 35.0, "explanation": "Diverse food group consumption protects nutritional reserves."},
                    {"name": "BMI", "direction": "Protective (toward Low)", "share": 30.0, "explanation": "Optimal body mass index supports physiological baseline."}
                ],
                bmi=21.3,
                model_version="v1.0-xgboost"
            )

            # Seed Assessment for Clinician 2 (ID = 2)
            self.aid_user2 = insert_assessment(
                db=db,
                user_id=3,
                subject="Patient Bob",
                inputs={
                    "age": 72, "sex": "Male", "height_cm": 170.0, "weight_kg": 48.0,
                    "food_groups": 2, "meals_per_day": 1, "activity": "Low",
                    "income": "Low", "education": "None", "residence": "Rural", "recent_illness": "Yes"
                },
                risk="High Risk",
                confidence=0.89,
                probabilities=[0.02, 0.09, 0.89],
                factors=[
                    {"name": "BMI", "direction": "Risk-increasing (toward High)", "share": 40.0, "explanation": "Severe underweight status indicates protein-energy wasting."},
                    {"name": "Age", "direction": "Risk-increasing (toward High)", "share": 25.0, "explanation": "Advanced age increases vulnerability to acute malnutrition."}
                ],
                bmi=16.61,
                model_version="v1.0-xgboost"
            )

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def login_user1(self):
        return self.client.post("/login", data={"email": "user1@clinic.org", "password": "UserOnePass888!"}, follow_redirects=True)

    def login_user2(self):
        return self.client.post("/login", data={"email": "user2@clinic.org", "password": "UserTwoPass777!"}, follow_redirects=True)

    def login_admin(self):
        return self.client.post("/login", data={"email": "admin@hospital.org", "password": "AdminSecurePass999!"}, follow_redirects=True)

    def test_unauthenticated_download_redirects(self):
        """Unauthenticated requests to download PDF must redirect to /login."""
        res = self.client.get(f"/result/{self.aid_user1}/pdf")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

    def test_user_can_download_own_pdf(self):
        """User 1 can download their own assessment PDF with proper headers and content."""
        self.login_user1()
        res = self.client.get(f"/result/{self.aid_user1}/pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "application/pdf")
        self.assertIn("attachment;", res.headers.get("Content-Disposition", ""))
        self.assertIn(f"NutriRisk_Assessment_{self.aid_user1}_", res.headers.get("Content-Disposition", ""))

        # Verify PDF binary header
        pdf_bytes = res.data
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Downloaded file does not start with PDF magic bytes.")
        self.assertGreater(len(pdf_bytes), 2000, "Downloaded PDF is suspiciously small.")

    def test_multi_tenant_privacy_isolation(self):
        """User 1 cannot download User 2's PDF assessment report (must return 404)."""
        self.login_user1()
        res = self.client.get(f"/result/{self.aid_user2}/pdf")
        self.assertEqual(res.status_code, 404, "User 1 must not be allowed to access User 2's PDF report.")

    def test_admin_can_download_any_pdf(self):
        """Administrator can download any assessment PDF across all users."""
        self.login_admin()
        # Admin downloads User 2's assessment
        res = self.client.get(f"/result/{self.aid_user2}/pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "application/pdf")
        self.assertTrue(res.data.startswith(b"%PDF-"))

    def test_nonexistent_assessment_returns_404(self):
        """Downloading an assessment that does not exist returns 404."""
        self.login_user1()
        res = self.client.get("/result/99999/pdf")
        self.assertEqual(res.status_code, 404)

    def test_direct_pdf_generation_and_a4_dimensions(self):
        """Verifies generate_assessment_pdf produces valid A4 PDF bytes without exposing sensitive data."""
        sample_record = {
            "id": 42,
            "subject": "John Doe",
            "risk": "Moderate Risk",
            "confidence": 0.76,
            "probs": "[0.12, 0.76, 0.12]",
            "factors": json.dumps([
                {"name": "Dietary Diversity", "direction": "Risk-increasing (toward Moderate)", "share": 45.0, "explanation": "Low daily fruit/vegetable variety."},
                {"name": "Meal Frequency", "direction": "Protective (toward Low)", "share": 25.0, "explanation": "3 regular meals per day."}
            ]),
            "bmi": 19.8,
            "model_version": "v1.0-xgboost",
            "created": "2026-10-21T14:30:00"
        }
        sample_inputs = {
            "age": 52, "sex": "Male", "height_cm": 172.0, "weight_kg": 58.6,
            "bmi": 19.8, "food_groups": 3, "meals_per_day": 3, "activity": "Moderate",
            "income": "Middle", "education": "Primary", "residence": "Urban", "recent_illness": "No"
        }

        pdf_buf = generate_assessment_pdf(
            assessment_record=sample_record,
            inputs_dict=sample_inputs,
            advice_text="Increase dietary diversity by introducing whole grains and legumes.",
            disclaimer_text="Academic clinical decision support prototype.",
            assessor_name="Dr. Senior Clinician",
            model_name="XGBoost Classifier"
        )

        pdf_bytes = pdf_buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertGreater(len(pdf_bytes), 3000)

        # Check standard A4 dimension markers in PDF: 595.27 x 841.89 points
        self.assertIn(b"595.27", pdf_bytes, "PDF does not declare standard A4 width.")
        self.assertTrue(b"841.88" in pdf_bytes or b"841.89" in pdf_bytes, "PDF does not declare standard A4 height.")

        # Strict Privacy: Zero exposure of passwords or hashes
        self.assertNotIn(b"AdminSecurePass999!", pdf_bytes)
        self.assertNotIn(b"UserOnePass888!", pdf_bytes)
        self.assertNotIn(b"scrypt:", pdf_bytes)
        self.assertNotIn(b"pbkdf2:", pdf_bytes)

    def test_pdf_generation_all_three_risk_tiers(self):
        """Verifies report generation across Low, Moderate, and High Risk tiers."""
        tiers = [
            ("Low Risk", 0.94, [0.94, 0.05, 0.01], 22.4),
            ("Moderate Risk", 0.72, [0.15, 0.72, 0.13], 18.9),
            ("High Risk", 0.88, [0.03, 0.09, 0.88], 15.5)
        ]

        for risk_name, conf, probs, bmi in tiers:
            rec = {
                "id": 101, "subject": f"Test {risk_name}", "risk": risk_name,
                "confidence": conf, "probs": json.dumps(probs), "factors": "[]",
                "bmi": bmi, "model_version": "v1.0-xgboost", "created": "2026-10-21T10:00:00"
            }
            inp = {"age": 40, "sex": "Female", "height_cm": 160.0, "weight_kg": 50.0, "bmi": bmi}
            buf = generate_assessment_pdf(rec, inp, "Follow protocol", "Disclaimer")
            self.assertTrue(buf.getvalue().startswith(b"%PDF-"))

    def test_pdf_generation_robustness_with_empty_or_malformed_json(self):
        """Verifies generator does not crash on malformed JSON or empty factors."""
        rec = {
            "id": 999, "subject": "Robustness Test", "risk": "Low Risk",
            "confidence": 0.90, "probs": "malformed_json", "factors": "{invalid}",
            "bmi": 0.0, "model_version": "v1.0-xgboost", "created": ""
        }
        inp = {"height_cm": 170.0, "weight_kg": 65.0}  # BMI can be computed
        buf = generate_assessment_pdf(rec, inp, "Advice", "Disclaimer")
        b = buf.getvalue()
        self.assertTrue(b.startswith(b"%PDF-"))
        self.assertGreater(len(b), 2000)

if __name__ == "__main__":
    unittest.main()
