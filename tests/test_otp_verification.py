"""
Automated Test Suite for OTP (One-Time Password) Verification in NutriRisk AI.

Covers:
  1. Cryptographic 6-digit OTP generation and invalidation of old codes.
  2. OTP expiration (10-minute window) and replay prevention (single-use validation).
  3. API endpoints:
     - POST /send-otp (and /auth/send-otp): generation, validation, non-existent user handling.
     - POST /verify-otp (and /auth/verify-otp): authentication, session creation, password reset.
  4. Web fallback interface:
     - GET /otp-login: renders passwordless authentication form.
     - POST /otp-login (action=send): dispatches code and displays demo feedback.
     - POST /otp-login (action=verify): validates code and redirects to dashboard.
"""

import unittest
import os
import tempfile
import json
from datetime import datetime, timedelta, timezone
from nutririsk import create_app
from nutririsk.db import get_db, create_otp, verify_otp
from nutririsk.auth.utils import hash_password, verify_password


class TestOTPVerification(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-otp-secret-key-12345",
            "WTF_CSRF_ENABLED": False,
            "ENFORCE_CSRF_IN_TESTS": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # Test user
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Test Clinician", "test.clinician@nutririsk.org", hash_password("Password123!"), "user", "2026-10-01T10:00:00")
            )
            db.commit()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def test_create_and_verify_otp_unit(self):
        """Test database helper functions directly."""
        with self.app.app_context():
            db = get_db()
            email = "test.clinician@nutririsk.org"

            # 1. Create OTP
            code = create_otp(db, email, purpose="login", validity_seconds=600)
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())

            # Verify in DB
            row = db.execute("SELECT * FROM otp_verifications WHERE email = ? AND otp = ?", (email, code)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["used"], 0)

            # 2. Verify with wrong code
            success, msg = verify_otp(db, email, "000000", purpose="login")
            self.assertFalse(success)
            self.assertIn("Incorrect verification code", msg)

            # 3. Verify with correct code
            success, msg = verify_otp(db, email, code, purpose="login")
            self.assertTrue(success)
            self.assertIn("successful", msg)

            # 4. Single-use: Re-verifying should fail
            success2, msg2 = verify_otp(db, email, code, purpose="login")
            self.assertFalse(success2)

    def test_otp_invalidation_on_new_request(self):
        """Requesting a new OTP should invalidate any previously active OTP for that email and purpose."""
        with self.app.app_context():
            db = get_db()
            email = "test.clinician@nutririsk.org"

            code1 = create_otp(db, email, purpose="login")
            code2 = create_otp(db, email, purpose="login")

            # Code1 should be invalidated (marked used)
            success1, _ = verify_otp(db, email, code1, purpose="login")
            self.assertFalse(success1)

            # Code2 should succeed
            success2, _ = verify_otp(db, email, code2, purpose="login")
            self.assertTrue(success2)

    def test_otp_expiry(self):
        """Expired OTPs must be rejected."""
        with self.app.app_context():
            db = get_db()
            email = "test.clinician@nutririsk.org"

            code = create_otp(db, email, purpose="login", validity_seconds=600)

            # Artificially expire the OTP
            past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            db.execute("UPDATE otp_verifications SET expires_at = ? WHERE email = ? AND otp = ?", (past_time, email, code))
            db.commit()

            success, msg = verify_otp(db, email, code, purpose="login")
            self.assertFalse(success)
            self.assertIn("expired", msg)

    def test_send_otp_api_endpoint(self):
        """Test POST /send-otp and /auth/send-otp."""
        # Invalid email format
        resp = self.client.post("/auth/send-otp", json={"email": "invalid-email"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("registered email address", resp.get_json()["message"])

        # Non-existent user
        resp = self.client.post("/auth/send-otp", json={"email": "nonexistent@hospital.org"})
        self.assertEqual(resp.status_code, 404)
        self.assertIn("No registered account", resp.get_json()["message"])

        # Valid registered user
        resp = self.client.post("/auth/send-otp", json={"email": "test.clinician@nutririsk.org", "purpose": "login"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("otp_preview", data)
        self.assertEqual(len(data["otp_preview"]), 6)

    def test_verify_otp_login_api_endpoint(self):
        """Test POST /verify-otp logs user in and creates session."""
        email = "test.clinician@nutririsk.org"
        with self.app.app_context():
            db = get_db()
            code = create_otp(db, email, purpose="login")

        # Wrong code
        resp = self.client.post("/auth/verify-otp", json={"email": email, "otp": "999999", "purpose": "login"})
        self.assertEqual(resp.status_code, 400)

        # Correct code
        resp = self.client.post("/auth/verify-otp", json={"email": email, "otp": code, "purpose": "login"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("redirect", data)

        # Check session established
        with self.client.session_transaction() as sess:
            self.assertIn("uid", sess)
            self.assertEqual(sess["name"], "Dr. Test Clinician")
            self.assertEqual(sess["role"], "user")

    def test_verify_otp_password_reset(self):
        """Test POST /verify-otp with purpose='reset' resets password."""
        email = "test.clinician@nutririsk.org"
        with self.app.app_context():
            db = get_db()
            code = create_otp(db, email, purpose="reset")

        # Reset with new password
        resp = self.client.post("/auth/verify-otp", json={
            "email": email,
            "otp": code,
            "purpose": "reset",
            "password": "NewSecurePassword456!"
        })
        self.assertEqual(resp.status_code, 200)

        # Verify password in DB updated
        with self.app.app_context():
            db = get_db()
            user = db.execute("SELECT pw FROM users WHERE email = ?", (email,)).fetchone()
            self.assertTrue(verify_password(user["pw"], "NewSecurePassword456!"))

    def test_otp_login_html_view(self):
        """Test dedicated /otp-login web view flow."""
        email = "test.clinician@nutririsk.org"

        # GET request
        resp = self.client.get("/otp-login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sign In with OTP", resp.data)

        # POST action=send
        resp = self.client.post("/otp-login", data={"email": email, "action": "send"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Verification code sent!", resp.data)
        self.assertIn(b"Demo Code:", resp.data)

        # Fetch code from DB
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT otp FROM otp_verifications WHERE email = ? AND used = 0", (email,)).fetchone()
            code = row["otp"]

        # POST action=verify
        resp = self.client.post("/otp-login", data={"email": email, "otp": code, "action": "verify"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Welcome back", resp.data)

        # Check authenticated session
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["name"], "Dr. Test Clinician")


if __name__ == "__main__":
    unittest.main()
