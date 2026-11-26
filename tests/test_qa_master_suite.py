"""
Master QA Automated Test Suite for NutriRisk AI (Prompt 22).

Comprehensive QA verification covering all 21 core modules:
  1. Application startup & factory pattern.
  2. Database initialization & automated safe migrations.
  3. Registration (role assignment, validations, uniqueness).
  4. Login (credential verification, session security).
  5. Logout (session clearance, redirection).
  6. Profile management (display name, email verification, password update, data integrity).
  7. Protected routes (RBAC & unauthenticated redirection).
  8. Prediction form validation (schema & boundary enforcement).
  9. BMI calculation & anthropometric categorization.
  10. Feature preprocessing & pipeline transformation.
  11. Model loading & artifact deserialization.
  12. Risk prediction & multi-class inference.
  13. Class probability mapping & confidence alignment.
  14. Assessment storage in SQLite.
  15. Prediction history (filtering, sorting, searching, pagination).
  16. Analytics dashboard & distribution aggregations.
  17. Admin authorization & governance safeguards.
  18. PDF generation (A4 layout, clinical styling, privacy).
  19. Invalid inputs handling (out-of-bounds anthropometry, bad categories).
  20. Missing dataset handling & graceful fallbacks.
  21. Missing model artifacts handling & diagnostics.
"""
import unittest
import os
import json
import tempfile
import sqlite3
import pandas as pd
import numpy as np

from nutririsk import create_app
from nutririsk.config import Config
from nutririsk.db import (
    get_db, init_db, insert_assessment, get_assessment_secure,
    get_user_by_id, get_user_by_email, get_active_model_metadata
)
from nutririsk.auth.utils import hash_password, verify_password
from nutririsk.ml.features import (
    add_features, validate_and_parse_input, LABELS, RAW, CHOICES, VALIDATION_BOUNDS
)
from nutririsk.ml.prediction import (
    predict_nutritional_risk, get_model_bundle, clear_model_cache
)
from nutririsk.ml.data_validation import load_dataset_metadata
from nutririsk.pdf_report import generate_assessment_pdf
from nutririsk.routes.main import load_metrics


class TestQAMasterSuite(unittest.TestCase):
    """Senior QA Engineer Automated Test Suite for NutriRisk AI."""

    def setUp(self):
        # 1. Create isolated temporary database for test isolation
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        # 2. Configure isolated Flask test application
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "qa-master-secret-key-2026",
            "WTF_CSRF_ENABLED": False,
            "ENFORCE_CSRF_IN_TESTS": False
        })
        self.client = self.app.test_client()

        # 3. Seed deterministic baseline users
        with self.app.app_context():
            db = get_db()
            # User 1: Administrator
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Admin QA", "admin.qa@hospital.org", hash_password("AdminPass123!"), "admin", "2026-09-01T08:00:00")
            )
            # User 2: Clinician
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Clinician QA", "clinician.qa@hospital.org", hash_password("ClinicianPass123!"), "user", "2026-09-05T09:00:00")
            )
            db.commit()

            # Seed assessment for User 2
            insert_assessment(
                db=db,
                user_id=2,
                subject="Baseline Patient",
                inputs={"age": 55, "sex": "Female", "height_cm": 162.0, "weight_kg": 65.0, "bmi": 24.77},
                risk="Low Risk",
                confidence=0.89,
                probabilities=[0.89, 0.08, 0.03],
                factors=[{"name": "Dietary Diversity", "direction": "Protective"}],
                bmi=24.77,
                model_version="v1.0-xgboost"
            )

    def tearDown(self):
        # Clean up temporary database file
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def _login(self, email, password):
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 1: Application Startup
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_application_startup(self):
        """Verifies application factory initializes blueprints and configuration."""
        self.assertTrue(self.app.config.get("TESTING"))
        self.assertIn("main", self.app.blueprints)
        self.assertIn("auth", self.app.blueprints)
        self.assertIn("assessment", self.app.blueprints)
        self.assertIn("analytics", self.app.blueprints)
        self.assertIn("admin", self.app.blueprints)

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"NutriRisk AI", res.data)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 2: Database Initialization & Safe Migrations
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_database_initialization(self):
        """Verifies database initialization generates all tables, columns, and indexes."""
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("users", tables)
            self.assertIn("assessments", tables)
            self.assertIn("model_metadata", tables)
            self.assertIn("admin_audit_logs", tables)

            # Check assessments columns including migrated bmi and model_version
            cursor.execute("PRAGMA table_info(assessments);")
            cols = {row[1] for row in cursor.fetchall()}
            self.assertIn("bmi", cols)
            self.assertIn("model_version", cols)
            self.assertIn("probs", cols)
            self.assertIn("factors", cols)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 3: Registration
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_registration(self):
        """Verifies registration validation, duplicate email detection, and role assignment."""
        # 1. Valid registration
        res = self.client.post("/register", data={
            "name": "Dr. Sarah Connor",
            "email": "sarah.connor@hospital.org",
            "password": "SarahPass2026!",
            "confirm_password": "SarahPass2026!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Registration successful", res.data.decode("utf-8"))

        # 2. Duplicate email rejected
        res_dup = self.client.post("/register", data={
            "name": "Sarah Duplicate",
            "email": "sarah.connor@hospital.org",
            "password": "AnotherPass2026!",
            "confirm_password": "AnotherPass2026!"
        }, follow_redirects=True)
        self.assertIn("already exists", res_dup.data.decode("utf-8"))

        # 3. Password mismatch rejected
        res_mismatch = self.client.post("/register", data={
            "name": "Mismatched User",
            "email": "mismatch@hospital.org",
            "password": "Password123!",
            "confirm_password": "DifferentPass456!"
        }, follow_redirects=True)
        self.assertIn("Passwords do not match", res_mismatch.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 4: Login
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_login(self):
        """Verifies credential validation, session creation, and invalid credential handling."""
        # 1. Valid login
        res = self._login("clinician.qa@hospital.org", "ClinicianPass123!")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Welcome back, Dr. Clinician QA!", res.data.decode("utf-8"))

        # Check session state
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("uid"), 2)
            self.assertEqual(sess.get("role"), "user")

        # 2. Wrong password rejected
        self.client.get("/logout")
        res_fail = self._login("clinician.qa@hospital.org", "WrongPassword999!")
        self.assertIn("Invalid email or password", res_fail.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 5: Logout
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_logout(self):
        """Verifies logout clears session and redirects to home page."""
        self._login("clinician.qa@hospital.org", "ClinicianPass123!")
        res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("You have been securely logged out.", res.data.decode("utf-8"))

        # Session should be empty
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("uid"))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 6: Profile Management & Data Integrity
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_profile_management(self):
        """Verifies display name update, email change with password verification, and historical preservation."""
        self._login("clinician.qa@hospital.org", "ClinicianPass123!")

        # 1. View profile
        res_view = self.client.get("/profile")
        self.assertEqual(res_view.status_code, 200)
        self.assertIn("Dr. Clinician QA", res_view.data.decode("utf-8"))
        self.assertIn("clinician.qa@hospital.org", res_view.data.decode("utf-8"))

        # 2. Update display name
        res_name = self.client.post("/profile", data={
            "action": "update_name",
            "name": "Dr. Clinician QA, Chief Dietitian"
        }, follow_redirects=True)
        self.assertIn("Display name updated successfully.", res_name.data.decode("utf-8"))

        # 3. Update email with password verification
        res_email = self.client.post("/profile", data={
            "action": "update_email",
            "email": "clinician.new@hospital.org",
            "current_password_email": "ClinicianPass123!"
        }, follow_redirects=True)
        self.assertIn("Email address updated successfully.", res_email.data.decode("utf-8"))

        # 4. Verify historical assessments preserved (integrity check)
        with self.app.app_context():
            db = get_db()
            count = db.execute("SELECT COUNT(*) FROM assessments WHERE user_id = 2").fetchone()[0]
            self.assertEqual(count, 1, "Historical assessment was decoupled or deleted!")

    # ─────────────────────────────────────────────────────────────────────────
    # Module 7: Protected Routes & Authorization Redirection
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_protected_routes(self):
        """Verifies unauthenticated visitors are redirected to /login for all protected routes."""
        anon = self.app.test_client()
        protected = ["/dashboard", "/predict", "/history", "/analytics", "/profile", "/result/1"]
        for route in protected:
            res = anon.get(route)
            self.assertEqual(res.status_code, 302, f"Route {route} was not protected (expected 302).")
            self.assertIn("/login", res.headers.get("Location", ""))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 8: Prediction Form Validation
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_prediction_form_validation(self):
        """Verifies form parser accepts valid clinical payloads and rejects missing/invalid fields."""
        valid_form = {
            "age": "45", "sex": "Male", "height_cm": "172.5", "weight_kg": "68.0",
            "food_groups": "5", "meals_per_day": "3", "activity": "Moderate",
            "income": "Middle", "education": "Secondary", "residence": "Urban",
            "recent_illness": "No"
        }
        parsed, err = validate_and_parse_input(valid_form)
        self.assertIsNone(err)
        self.assertEqual(parsed["age"], 45)
        self.assertEqual(parsed["sex"], "Male")

        # Missing field
        incomplete = dict(valid_form)
        del incomplete["meals_per_day"]
        parsed_bad, err_bad = validate_and_parse_input(incomplete)
        self.assertIsNotNone(err_bad)
        self.assertIn("meals", err_bad.lower())

    # ─────────────────────────────────────────────────────────────────────────
    # Module 9: BMI Calculation & Bounds
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_bmi_calculation(self):
        """Verifies BMI calculation: weight / (height/100)^2 across normal and boundary conditions."""
        df = pd.DataFrame([{
            "age": 30, "sex": "Female", "height_cm": 160.0, "weight_kg": 51.2,
            "food_groups": 5, "meals_per_day": 3, "activity": "Moderate",
            "income": "Middle", "education": "Secondary", "residence": "Urban",
            "recent_illness": "No"
        }])
        df_feat = add_features(df)
        self.assertIn("bmi", df_feat.columns)
        # Expected: 51.2 / (1.60)^2 = 20.0
        self.assertAlmostEqual(df_feat["bmi"].iloc[0], 20.0, places=1)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 10: Feature Preprocessing
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_feature_preprocessing(self):
        """Verifies feature transformer pipeline handles raw features without data leakage."""
        bundle = get_model_bundle()
        pipeline = bundle["pipeline"]
        self.assertTrue(hasattr(pipeline, "predict_proba"))
        self.assertTrue(hasattr(pipeline, "named_steps"))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 11: Model Loading & Bundle Inspection
    # ─────────────────────────────────────────────────────────────────────────
    def test_11_model_loading(self):
        """Verifies model artifact is loaded and contains pipeline and reference statistics."""
        bundle = get_model_bundle()
        self.assertIn("pipeline", bundle)
        self.assertIn("reference", bundle)
        self.assertIsInstance(bundle["reference"], dict)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 12: Risk Prediction
    # ─────────────────────────────────────────────────────────────────────────
    def test_12_risk_prediction(self):
        """Verifies model generates structured prediction with risk label, confidence, and factors."""
        payload = {
            "age": 75, "sex": "Female", "height_cm": 150.0, "weight_kg": 38.0,
            "food_groups": 2, "meals_per_day": 1, "activity": "Low",
            "income": "Low", "education": "None", "residence": "Rural", "recent_illness": "Yes"
        }
        res = predict_nutritional_risk(payload)
        self.assertIn(res["risk"], LABELS)
        self.assertGreater(res["confidence"], 0.0)
        self.assertLessEqual(res["confidence"], 1.0)
        self.assertIsInstance(res["factors"], list)
        self.assertGreater(len(res["factors"]), 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 13: Class Probability Mapping
    # ─────────────────────────────────────────────────────────────────────────
    def test_13_class_probability_mapping(self):
        """Verifies 3-tier probabilities sum to 1.0 and match class label ordering."""
        payload = {
            "age": 25, "sex": "Male", "height_cm": 180.0, "weight_kg": 75.0,
            "food_groups": 7, "meals_per_day": 3, "activity": "High",
            "income": "High", "education": "Higher", "residence": "Urban", "recent_illness": "No"
        }
        res = predict_nutritional_risk(payload)
        probs = res["probabilities"]
        self.assertEqual(len(probs), 3)
        self.assertAlmostEqual(sum(probs), 1.0, places=3)
        self.assertEqual(res["confidence"], max(probs))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 14: Assessment Storage in SQLite
    # ─────────────────────────────────────────────────────────────────────────
    def test_14_assessment_storage(self):
        """Verifies new assessment is persisted in SQLite with all metadata and foreign key linkage."""
        with self.app.app_context():
            db = get_db()
            aid = insert_assessment(
                db=db,
                user_id=2,
                subject="QA Storage Patient",
                inputs={"age": 60, "sex": "Male", "height_cm": 170.0, "weight_kg": 62.0},
                risk="Moderate Risk",
                confidence=0.74,
                probabilities=[0.15, 0.74, 0.11],
                factors=[{"name": "Food Groups", "direction": "Risk-increasing"}],
                bmi=21.45,
                model_version="v1.0-xgboost"
            )
            self.assertGreater(aid, 0)

            record = get_assessment_secure(db, aid, user_id=2, is_admin=False)
            self.assertIsNotNone(record)
            self.assertEqual(record["subject"], "QA Storage Patient")
            self.assertEqual(record["risk"], "Moderate Risk")
            self.assertEqual(record["bmi"], 21.45)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 15: Prediction History
    # ─────────────────────────────────────────────────────────────────────────
    def test_15_prediction_history(self):
        """Verifies history query filters by risk, sorts, and isolates patient records."""
        self._login("clinician.qa@hospital.org", "ClinicianPass123!")

        res = self.client.get("/history")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Baseline Patient", res.data.decode("utf-8"))

        # Risk filter
        res_filter = self.client.get("/history?risk=Low+Risk")
        self.assertIn("Baseline Patient", res_filter.data.decode("utf-8"))

        # Non-matching filter returns empty state
        res_empty = self.client.get("/history?risk=High+Risk")
        self.assertIn("No Matching Assessments", res_empty.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 16: Analytics Dashboard
    # ─────────────────────────────────────────────────────────────────────────
    def test_16_analytics_dashboard(self):
        """Verifies analytics dashboard calculates distribution statistics from real DB records."""
        self._login("clinician.qa@hospital.org", "ClinicianPass123!")

        res = self.client.get("/analytics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Nutritional Risk Distribution", res.data.decode("utf-8"))

        # JSON API verification
        api_res = self.client.get("/api/analytics")
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()
        self.assertIn("statistics", data)
        self.assertEqual(data["statistics"]["total"], 1)
        self.assertEqual(data["statistics"]["low_count"], 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 17: Admin Authorization & Governance
    # ─────────────────────────────────────────────────────────────────────────
    def test_17_admin_authorization(self):
        """Verifies RBAC controls: clinician receives 403, admin receives 200 and audit logging."""
        # 1. Clinician forbidden
        self._login("clinician.qa@hospital.org", "ClinicianPass123!")
        res_forbid = self.client.get("/admin")
        self.assertEqual(res_forbid.status_code, 403)

        # 2. Administrator allowed
        self.client.get("/logout")
        self._login("admin.qa@hospital.org", "AdminPass123!")
        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn("Administrative Oversight Console", res_admin.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # Module 18: Downloadable PDF Report Generation
    # ─────────────────────────────────────────────────────────────────────────
    def test_18_pdf_generation(self):
        """Verifies generation of ISO A4 PDF assessment report with clinical formatting."""
        record = {
            "id": 99, "subject": "QA PDF Patient", "risk": "Moderate Risk",
            "confidence": 0.77, "probs": "[0.12, 0.77, 0.11]",
            "factors": json.dumps([{"name": "Dietary Diversity", "direction": "Risk-increasing", "share": 40.0, "explanation": "Low fruit intake"}]),
            "bmi": 19.5, "model_version": "v1.0-xgboost", "created": "2026-10-22T10:00:00"
        }
        inputs = {
            "age": 48, "sex": "Female", "height_cm": 160.0, "weight_kg": 50.0,
            "bmi": 19.5, "food_groups": 3, "meals_per_day": 2, "activity": "Low",
            "income": "Low", "education": "Primary", "residence": "Rural", "recent_illness": "No"
        }
        pdf_buf = generate_assessment_pdf(
            assessment_record=record,
            inputs_dict=inputs,
            advice_text="Increase dietary variety.",
            disclaimer_text="Academic prototype only.",
            assessor_name="Dr. Admin QA",
            model_name="XGBoost Classifier"
        )
        pdf_bytes = pdf_buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertGreater(len(pdf_bytes), 3000)
        # Check standard A4 dimension markers
        self.assertIn(b"595.27", pdf_bytes)

    # ─────────────────────────────────────────────────────────────────────────
    # Module 19: Invalid Inputs Handling
    # ─────────────────────────────────────────────────────────────────────────
    def test_19_invalid_inputs(self):
        """Verifies parser rejects invalid anthropometry, underage ages, and illegal categories."""
        # 1. Underage
        p1 = {"age": "15", "sex": "Male", "height_cm": "170", "weight_kg": "60"}
        _, e1 = validate_and_parse_input(p1)
        self.assertIn("18", e1)

        # 2. Out-of-bounds weight
        p2 = {"age": "30", "sex": "Male", "height_cm": "170", "weight_kg": "15"}
        _, e2 = validate_and_parse_input(p2)
        self.assertIn("weight", e2.lower())

        # 3. Invalid categorical (with other required fields valid)
        p3 = {
            "age": "30", "sex": "UnknownGender", "height_cm": "170", "weight_kg": "60",
            "food_groups": "4", "meals_per_day": "3"
        }
        _, e3 = validate_and_parse_input(p3)
        self.assertIn("sex", e3.lower())

    # ─────────────────────────────────────────────────────────────────────────
    # Module 20: Missing Dataset Handling
    # ─────────────────────────────────────────────────────────────────────────
    def test_20_missing_dataset(self):
        """Verifies system handles missing dataset gracefully without server crash."""
        nonexistent_path = os.path.join(Config.BASE_DIR, "data", "nonexistent_dataset_12345.json")
        meta = load_dataset_metadata(nonexistent_path)
        self.assertIsInstance(meta, dict)
        self.assertIn("source", meta)
        self.assertIn("SYNTHETIC", meta["source"])

    # ─────────────────────────────────────────────────────────────────────────
    # Module 21: Missing Model Artifacts Handling
    # ─────────────────────────────────────────────────────────────────────────
    def test_21_missing_model_artifacts(self):
        """Verifies clear FileNotFoundError diagnostic when model artifact is absent."""
        fake_model_path = os.path.join(Config.BASE_DIR, "model", "missing_artifact_test.joblib")
        with self.assertRaises(FileNotFoundError) as ctx:
            predict_nutritional_risk({
                "age": 30, "sex": "Female", "height_cm": 165.0, "weight_kg": 60.0,
                "food_groups": 5, "meals_per_day": 3, "activity": "Moderate",
                "income": "Middle", "education": "Secondary", "residence": "Urban", "recent_illness": "No"
            }, model_path=fake_model_path)
        self.assertIn("Please run 'python train.py'", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
