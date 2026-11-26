"""
NutriRisk AI — Automated Batch Patient Screening Test Suite.

Verifies:
  1. Route access control (unauthenticated redirected to /login).
  2. Sample CSV template download integrity.
  3. Rejection of invalid file types and missing files.
  4. Header validation and error diagnostics.
  5. Successful end-to-end multi-patient CSV stratification and database persistence.
  6. Resilient handling of mixed valid and malformed rows.
"""
import io
import os
import tempfile
import unittest

from nutririsk import create_app
from nutririsk.db import get_db
from nutririsk.auth.utils import hash_password


class TestBatchPatientScreening(unittest.TestCase):
    """Integration test suite for the batch screening module."""

    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db.close()
        cls.test_db_path = cls.temp_db.name

        cls.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": cls.test_db_path,
            "SECRET_KEY": "batch-screening-test-secret-key-12345",
            "WTF_CSRF_ENABLED": False,
            "ENFORCE_CSRF_IN_TESTS": False
        })

        with cls.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Batch Clinician", "batch.doc@hospital.org", hash_password("ClinicianPass123!"), "user", "2026-09-01T08:00:00")
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

    def _login(self):
        return self.client.post("/login", data={
            "email": "batch.doc@hospital.org",
            "password": "ClinicianPass123!"
        }, follow_redirects=True)

    def test_01_unauthenticated_access_redirects(self):
        """Unauthenticated requests to /batch must redirect to /login."""
        resp = self.client.get("/batch")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_02_sample_template_download(self):
        """Sample template route must stream a valid CSV file with expected headers."""
        self._login()
        resp = self.client.get("/batch/sample-template")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "text/csv; charset=utf-8")
        csv_text = resp.get_data(as_text=True)
        self.assertIn("subject,age,sex,height_cm,weight_kg,food_groups", csv_text)
        self.assertIn("Patient Alpha", csv_text)

    def test_03_no_file_uploaded(self):
        """Posting without a file should flash an error and re-render."""
        self._login()
        resp = self.client.post("/batch", data={}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Please select a valid CSV file", resp.get_data(as_text=True))

    def test_04_invalid_file_extension(self):
        """Posting a non-CSV file should be rejected."""
        self._login()
        data = {
            "csv_file": (io.BytesIO(b"Hello world"), "test.txt")
        }
        resp = self.client.post("/batch", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Invalid file format", resp.get_data(as_text=True))

    def test_05_missing_headers_diagnostic(self):
        """Uploading a CSV missing mandatory columns provides clear feedback."""
        self._login()
        incomplete_csv = "subject,age,sex\nPatient 1,45,Male\n"
        data = {
            "csv_file": (io.BytesIO(incomplete_csv.encode("utf-8")), "incomplete.csv")
        }
        resp = self.client.post("/batch", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("CSV header is missing required column", resp.get_data(as_text=True))

    def test_06_successful_batch_stratification(self):
        """Valid multi-patient CSV is parsed, stratified, and persisted into SQLite."""
        self._login()
        valid_csv = (
            "subject,age,sex,height_cm,weight_kg,food_groups,meals_per_day,activity,income,education,residence,recent_illness\n"
            "Ward Patient A,72,Female,155,38,2,2,Low,Low,Primary,Rural,Yes\n"
            "Ward Patient B,42,Male,172,68,5,3,Moderate,Middle,Secondary,Urban,No\n"
            "Ward Patient C,25,Female,165,60,7,4,High,High,Higher,Urban,No\n"
        )
        data = {
            "csv_file": (io.BytesIO(valid_csv.encode("utf-8")), "ward_patients.csv")
        }
        resp = self.client.post("/batch", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn("Batch screening complete", html)
        self.assertIn("Ward Patient A", html)
        self.assertIn("Ward Patient B", html)
        self.assertIn("Ward Patient C", html)

        # Verify database records were persisted
        with self.app.app_context():
            db = get_db()
            rows = db.execute("SELECT * FROM assessments WHERE subject LIKE 'Ward Patient %'").fetchall()
            self.assertEqual(len(rows), 3, "Database should contain all 3 persisted assessments")
            for r in rows:
                self.assertIn(r["risk"], ["Low Risk", "Moderate Risk", "High Risk"])
                self.assertGreater(r["bmi"], 10.0)

    def test_07_mixed_valid_and_invalid_rows_resilience(self):
        """Processes valid rows while logging descriptive diagnostics for invalid rows."""
        self._login()
        mixed_csv = (
            "subject,age,sex,height_cm,weight_kg,food_groups,meals_per_day,activity,income,education,residence,recent_illness\n"
            "Valid Subject 1,50,Male,170,65,4,3,Moderate,Middle,Secondary,Urban,No\n"
            "Underage Subject,12,Female,150,45,4,3,Moderate,Middle,Secondary,Urban,No\n"
            "Invalid Weight Subject,40,Male,170,12,4,3,Moderate,Middle,Secondary,Urban,No\n"
            "Valid Subject 2,60,Female,160,55,5,3,Low,Middle,Primary,Rural,No\n"
        )
        data = {
            "csv_file": (io.BytesIO(mixed_csv.encode("utf-8")), "mixed_cohort.csv")
        }
        resp = self.client.post("/batch", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn("Successfully stratified 2 of 4 patient records", html)
        self.assertIn("Validation Exclusions (2 Rows Skipped)", html)
        self.assertIn("Valid Subject 1", html)
        self.assertIn("Valid Subject 2", html)


if __name__ == "__main__":
    unittest.main()
