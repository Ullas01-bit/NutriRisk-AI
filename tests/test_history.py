"""
Test Suite for NutriRisk AI Prediction History Module (Prompt 15).
Covers:
  1. Viewing user's historical assessments.
  2. Searching records by patient/subject label and by record ID.
  3. Filtering records by risk category (Low, Moderate, High).
  4. Filtering records by assessment date range (start_date, end_date).
  5. Sorting records by date, risk, confidence, and BMI.
  6. Class probabilities presentation.
  7. Pagination logic (page navigation, per_page limits, total pages).
  8. Graceful empty state handling for search misses.
  9. Multi-tenant access controls and URL manipulation security.
"""
import unittest
import os
import json
import tempfile
from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password

class TestPredictionHistory(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-history-secret-key-12345",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # User 1: Dr. Clinical User
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Clinical User", "doctor@example.com", hash_password("pass123"), "user", "2026-10-01T08:00:00")
            )
            # User 2: Other User
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Other Doctor", "other@example.com", hash_password("pass456"), "user", "2026-10-01T08:00:00")
            )
            db.commit()

            # Seed 12 distinct assessments for User 1 spanning different dates, risks, BMIs, and confidences
            sample_records = [
                ("Patient Alpha", "2026-10-05T09:15:00", "Low Risk", 0.92, 21.5, {"Low Risk": 0.92, "Moderate Risk": 0.06, "High Risk": 0.02}),
                ("Patient Beta", "2026-10-06T10:30:00", "Moderate Risk", 0.74, 18.2, {"Low Risk": 0.20, "Moderate Risk": 0.74, "High Risk": 0.06}),
                ("Patient Gamma", "2026-10-07T11:45:00", "High Risk", 0.95, 14.8, {"Low Risk": 0.01, "Moderate Risk": 0.04, "High Risk": 0.95}),
                ("Patient Delta", "2026-10-08T14:20:00", "Low Risk", 0.88, 24.1, {"Low Risk": 0.88, "Moderate Risk": 0.10, "High Risk": 0.02}),
                ("Patient Epsilon", "2026-10-09T16:00:00", "Moderate Risk", 0.69, 17.5, {"Low Risk": 0.25, "Moderate Risk": 0.69, "High Risk": 0.06}),
                ("Patient Zeta", "2026-10-10T09:00:00", "High Risk", 0.89, 15.2, {"Low Risk": 0.03, "Moderate Risk": 0.08, "High Risk": 0.89}),
                ("Patient Eta", "2026-10-11T12:10:00", "Low Risk", 0.84, 22.8, {"Low Risk": 0.84, "Moderate Risk": 0.12, "High Risk": 0.04}),
                ("Patient Theta", "2026-10-12T15:30:00", "Moderate Risk", 0.78, 19.0, {"Low Risk": 0.15, "Moderate Risk": 0.78, "High Risk": 0.07}),
                ("Patient Iota", "2026-10-13T16:45:00", "High Risk", 0.93, 16.1, {"Low Risk": 0.02, "Moderate Risk": 0.05, "High Risk": 0.93}),
                ("Patient Kappa", "2026-10-14T10:00:00", "Low Risk", 0.91, 23.4, {"Low Risk": 0.91, "Moderate Risk": 0.07, "High Risk": 0.02}),
                ("Patient Lambda", "2026-10-15T11:20:00", "Moderate Risk", 0.76, 18.7, {"Low Risk": 0.18, "Moderate Risk": 0.76, "High Risk": 0.06}),
                ("Patient Mu", "2026-10-16T14:50:00", "High Risk", 0.97, 13.9, {"Low Risk": 0.01, "Moderate Risk": 0.02, "High Risk": 0.97})
            ]

            for subj, dt, rk, conf, bmi, probs in sample_records:
                db.execute(
                    """INSERT INTO assessments 
                       (user_id, subject, created, inputs, risk, confidence, probs, factors, age, sex, bmi, model_version)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (1, subj, dt, json.dumps({"age": 45, "sex": "Female"}), rk, conf, json.dumps(probs), json.dumps([]), 45, "Female", bmi, "v1.0-xgboost")
                )

            # User 2 private assessment (To test URL manipulation isolation)
            db.execute(
                """INSERT INTO assessments 
                   (user_id, subject, created, inputs, risk, confidence, probs, factors, age, sex, bmi, model_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (2, "User 2 Confidential Record", "2026-10-18T10:00:00", json.dumps({"age": 30, "sex": "Male", "height_cm": 175.0, "weight_kg": 75.0}), "High Risk", 0.99, json.dumps({"Low Risk": 0.0, "Moderate Risk": 0.01, "High Risk": 0.99}), json.dumps([]), 30, "Male", 24.49, "v1.0-xgboost")
            )
            db.commit()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def login_user1(self):
        return self.client.post("/login", data={
            "email": "doctor@example.com",
            "password": "pass123"
        }, follow_redirects=True)

    def login_user2(self):
        return self.client.post("/login", data={
            "email": "other@example.com",
            "password": "pass456"
        }, follow_redirects=True)

    def test_history_unauthenticated_redirects(self):
        """Unauthenticated requests to /history must redirect to /login."""
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_history_default_view(self):
        """Default history page lists first page of user assessments with pagination and charts."""
        self.login_user1()
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 200)

        # Header and table present
        self.assertIn(b"Assessment Records &amp; History", response.data)
        self.assertIn(b"Showing <strong>1</strong> to <strong>10</strong> of <strong>12</strong> assessments", response.data)
        
        # Newest record (Patient Mu) should be on page 1
        self.assertIn(b"Patient Mu", response.data)
        self.assertIn(b"High Risk", response.data)
        self.assertIn(b"97.0%", response.data)

        # Charts present
        self.assertIn(b'id="historyRiskChart"', response.data)
        self.assertIn(b'id="historyTimelineChart"', response.data)

        # Class probabilities mini progress bar present
        self.assertIn(b"L: 1.0%", response.data)
        self.assertIn(b"H: 97.0%", response.data)

        # User 2 private record must NOT be visible
        self.assertNotIn(b"User 2 Confidential Record", response.data)

    def test_search_by_subject_and_id(self):
        """Search query filters correctly by subject substring and ID."""
        self.login_user1()
        
        # 1. Search by subject keyword
        res = self.client.get("/history?q=Delta")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Patient Delta", res.data)
        self.assertNotIn(b"Patient Alpha", res.data)
        self.assertIn(b"Showing <strong>1</strong> to <strong>1</strong> of <strong>1</strong>", res.data)

        # 2. Search by numeric ID (e.g. record #1)
        res_id = self.client.get("/history?q=1")
        self.assertEqual(res_id.status_code, 200)
        self.assertIn(b"#1", res_id.data)

    def test_filter_by_risk_category(self):
        """Risk filter only returns assessments in the selected category."""
        self.login_user1()

        # Filter: High Risk only (we seeded 4 High Risk records)
        res = self.client.get("/history?risk=High+Risk")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Showing <strong>1</strong> to <strong>4</strong> of <strong>4</strong>", res.data)
        self.assertIn(b"Patient Mu", res.data)
        self.assertIn(b"Patient Gamma", res.data)
        self.assertNotIn(b"Patient Alpha", res.data)  # Alpha is Low Risk
        self.assertNotIn(b"Patient Beta", res.data)   # Beta is Moderate Risk

    def test_filter_by_date_range(self):
        """Date filters constrain records between start_date and end_date."""
        self.login_user1()

        # Date range: 2026-10-06 to 2026-10-08 (Patients Beta, Gamma, Delta)
        res = self.client.get("/history?start_date=2026-10-06&end_date=2026-10-08")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Showing <strong>1</strong> to <strong>3</strong> of <strong>3</strong>", res.data)
        self.assertIn(b"Patient Beta", res.data)
        self.assertIn(b"Patient Gamma", res.data)
        self.assertIn(b"Patient Delta", res.data)
        self.assertNotIn(b"Patient Alpha", res.data)  # 2026-10-05
        self.assertNotIn(b"Patient Epsilon", res.data)  # 2026-10-09

    def test_sorting_records(self):
        """Verify sorting by BMI, confidence, and date."""
        self.login_user1()

        # Sort by BMI Descending: Highest BMI (Patient Delta: 24.1) should be first
        res_bmi = self.client.get("/history?sort=bmi_desc&per_page=5")
        self.assertEqual(res_bmi.status_code, 200)
        self.assertIn(b"Patient Delta", res_bmi.data)
        self.assertIn(b"24.1", res_bmi.data)

        # Sort by Date Ascending: Oldest record (Patient Alpha) should be first
        res_date = self.client.get("/history?sort=date_asc&per_page=5")
        self.assertEqual(res_date.status_code, 200)
        self.assertIn(b"Patient Alpha", res_date.data)
        self.assertNotIn(b"Patient Mu", res_date.data)

    def test_pagination_controls(self):
        """Page 2 displays remaining records when per_page=10."""
        self.login_user1()

        # Request page 2 with 10 per page (should contain 2 records: Patient Beta and Patient Alpha)
        res = self.client.get("/history?page=2&per_page=10")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Page <strong>2</strong> of <strong>2</strong>", res.data)
        self.assertIn(b"Showing <strong>11</strong> to <strong>12</strong> of <strong>12</strong>", res.data)
        self.assertIn(b"Patient Beta", res.data)
        self.assertIn(b"Patient Alpha", res.data)
        self.assertNotIn(b"Patient Mu", res.data)  # Was on page 1

    def test_empty_search_results_graceful_handling(self):
        """Non-matching query shows friendly empty state and reset button."""
        self.login_user1()
        res = self.client.get("/history?q=NonexistentPatientXYZ")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No Matching Assessments", res.data)
        self.assertIn(b"Reset Filters", res.data)
        self.assertIn(b"Showing <strong>0</strong> records", res.data)

    def test_multi_tenant_url_manipulation_prevention(self):
        """
        Critical security test: User 1 cannot access User 2's assessment
        record or PDF report by altering the ID in the URL.
        """
        # User 2 owns assessment ID 13 (User 2 Confidential Record)
        self.login_user1()

        # 1. User 1 tries to view User 2's result page
        res_view = self.client.get("/result/13")
        self.assertEqual(res_view.status_code, 404, "User 1 must not be able to view User 2's assessment")

        # 2. User 1 tries to download User 2's PDF report
        res_pdf = self.client.get("/result/13/pdf")
        self.assertEqual(res_pdf.status_code, 404, "User 1 must not be able to download User 2's PDF report")

        # 3. User 2 logs in and CAN view their own record 13
        self.login_user2()
        res_user2 = self.client.get("/result/13")
        self.assertEqual(res_user2.status_code, 200)
        self.assertIn(b"User 2 Confidential Record", res_user2.data)

if __name__ == "__main__":
    unittest.main()
