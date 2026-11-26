"""
NutriRisk AI — Face ID Biometric Authentication & Under 18 Scope Alert Test Suite.

Verifies:
  1. Face ID enrollment endpoints and database persistence.
  2. Face ID biometric login workflow and session establishment.
  3. Rejection of un-enrolled accounts during Face ID login.
  4. Face ID status query endpoint.
  5. Under 18 clinical alert modal and JavaScript triggers in /predict template.
  6. Server-side rejection of underage patient submissions (Adult 18+ boundary).
"""
import os
import json
import tempfile
import unittest

from nutririsk import create_app
from nutririsk.db import get_db
from nutririsk.auth.utils import hash_password


class TestFaceIdAndUnder18Features(unittest.TestCase):
    """Test suite for Face ID biometric login and under-18 pediatric alert pop-ups."""

    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db.close()
        cls.test_db_path = cls.temp_db.name

        cls.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": cls.test_db_path,
            "SECRET_KEY": "faceid-under18-test-key-9999",
            "WTF_CSRF_ENABLED": False,
            "ENFORCE_CSRF_IN_TESTS": False
        })

        with cls.app.app_context():
            db = get_db()
            # Enrolled user (User 1)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created, face_enrolled, face_descriptor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("Dr. Biometric", "biometric@hospital.org", hash_password("BioPass123!"), "user", "2026-09-01T08:00:00", 0, "")
            )
            # Regular user not enrolled (User 2)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created, face_enrolled, face_descriptor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("Dr. Standard", "standard@hospital.org", hash_password("StandardPass123!"), "user", "2026-09-01T08:00:00", 0, "")
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

    def _login_biometric_user(self):
        return self.client.post("/login", data={
            "email": "biometric@hospital.org",
            "password": "BioPass123!"
        }, follow_redirects=True)

    def test_01_face_enroll_requires_login(self):
        """Unauthenticated call to /auth/face-enroll must be rejected."""
        resp = self.client.post("/auth/face-enroll", json={"image_data": "data:image/jpeg;base64,mock"})
        self.assertEqual(resp.status_code, 302)

    def test_02_face_enroll_success_and_db_update(self):
        """Authenticated user can enroll Face ID with biometric frame."""
        self._login_biometric_user()
        mock_image = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        resp = self.client.post("/auth/face-enroll", json={"image_data": mock_image})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.get_data(as_text=True))
        self.assertEqual(data["status"], "success")

        # Verify database record reflects enrollment
        with self.app.app_context():
            db = get_db()
            user = db.execute("SELECT face_enrolled, face_descriptor FROM users WHERE email = 'biometric@hospital.org'").fetchone()
            self.assertEqual(user["face_enrolled"], 1)
            self.assertGreater(len(user["face_descriptor"]), 10)

    def test_03_face_status_endpoint(self):
        """Status endpoint correctly reflects enrolled vs non-enrolled accounts."""
        # Enrolled account
        resp_enrolled = self.client.get("/auth/face-status?email=biometric@hospital.org")
        self.assertEqual(resp_enrolled.status_code, 200)
        self.assertTrue(json.loads(resp_enrolled.get_data(as_text=True))["enrolled"])

        # Un-enrolled account
        resp_unenrolled = self.client.get("/auth/face-status?email=standard@hospital.org")
        self.assertEqual(resp_unenrolled.status_code, 200)
        self.assertFalse(json.loads(resp_unenrolled.get_data(as_text=True))["enrolled"])

    def test_04_face_login_unenrolled_account_rejected(self):
        """Attempting Face ID login for an un-enrolled account returns explanatory error."""
        self.client.get("/logout")
        mock_image = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        resp = self.client.post("/auth/face-login", json={
            "email": "standard@hospital.org",
            "image_data": mock_image
        })
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.get_data(as_text=True))
        self.assertEqual(data["status"], "error")
        self.assertIn("not enrolled", data["message"].lower())

    def test_05_face_login_success(self):
        """Enrolled user successfully authenticates via Face ID and session is established."""
        self.client.get("/logout")
        mock_image = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        resp = self.client.post("/auth/face-login", json={
            "email": "biometric@hospital.org",
            "image_data": mock_image
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.get_data(as_text=True))
        self.assertEqual(data["status"], "success")
        self.assertIn("/dashboard", data["redirect"])

        # Verify session is authenticated
        with self.client.session_transaction() as sess:
            self.assertIn("uid", sess)
            self.assertEqual(sess["name"], "Dr. Biometric")

    def test_06_under18_modal_markup_present(self):
        """Assessment template must contain the under 18 modal markup, ID, and WHO clinical alert."""
        self._login_biometric_user()
        resp = self.client.get("/predict")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn('id="inputAge"', html, "Age input must have inputAge ID for dynamic listener")
        self.assertIn('id="under18AlertModal"', html, "Template must include under 18 modal")
        self.assertIn("Pediatric Scope Limitation (Under 18)", html)
        self.assertIn("WHO Child Growth Standards", html)
        self.assertIn("btnResetAge", html)
        self.assertIn("btnSetAge18", html)

    def test_07_underage_submission_server_side_rejected(self):
        """Submitting an assessment with age < 18 is strictly rejected by server-side validation."""
        self._login_biometric_user()
        underage_payload = {
            "subject": "Pediatric Case",
            "age": "14",
            "sex": "Female",
            "height_cm": "150.0",
            "weight_kg": "40.0",
            "food_groups": "4",
            "meals_per_day": "3",
            "activity": "Moderate",
            "income": "Middle",
            "education": "Primary",
            "residence": "Urban",
            "recent_illness": "No"
        }
        resp = self.client.post("/predict", data=underage_payload, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Age must be between 18 and 100 years", html)


if __name__ == "__main__":
    unittest.main()
