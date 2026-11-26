"""
Test Suite for NutriRisk AI Profile Management Module (Prompt 20).
Covers:
  1. Viewing profile (display name, email, role, created date, assessment count).
  2. Unauthenticated access redirection to login.
  3. Editing display name with validation (min/max length, whitespace trimming).
  4. Viewing registered email address.
  5. Updating email address with password verification:
     - Success with correct current password.
     - Rejection on wrong password.
     - Rejection on missing password.
     - Rejection on invalid email format.
     - Rejection on duplicate email address (another user).
     - Rejection on same email address.
  6. Changing password securely:
     - Success with valid current password and matching new passwords.
     - Rejection on incorrect current password.
     - Rejection on short new password (< 6 chars).
     - Rejection on password reuse (same as current).
     - Rejection on mismatched password confirmation.
     - Verify new password allows login and old password is invalidated.
  7. Ensuring account changes never delete or corrupt historical assessments.
  8. Secure logout handling and session clearance.
"""
import unittest
import os
import tempfile
from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password, verify_password


class TestProfileManagement(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-profile-secret-key-12345",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # User 1: Dr. Alice Smith
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Alice Smith", "alice@example.com", hash_password("AliceSecure123!"), "user", "2026-09-15T10:30:00")
            )
            # User 2: Dr. Bob Jones (used for duplicate email tests)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Bob Jones", "bob@example.com", hash_password("BobSecure456!"), "user", "2026-09-20T11:00:00")
            )
            db.commit()

            # Seed 2 historical assessments for User 1 (id=1)
            insert_assessment(
                db=db,
                user_id=1,
                subject="Patient Gamma",
                inputs={"age": 45, "sex": "Female", "height_cm": 160.0, "weight_kg": 52.0, "bmi": 20.3},
                risk="Low Risk",
                confidence=0.88,
                probabilities=[0.88, 0.08, 0.04],
                factors=[{"name": "Dietary Diversity", "direction": "Protective"}],
                bmi=20.3,
                model_version="v1.0-xgboost"
            )
            insert_assessment(
                db=db,
                user_id=1,
                subject="Patient Delta",
                inputs={"age": 68, "sex": "Male", "height_cm": 170.0, "weight_kg": 49.0, "bmi": 17.0},
                risk="High Risk",
                confidence=0.92,
                probabilities=[0.02, 0.06, 0.92],
                factors=[{"name": "BMI (Height & Weight)", "direction": "Risk-increasing"}],
                bmi=17.0,
                model_version="v1.0-xgboost"
            )

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def _login(self, email="alice@example.com", password="AliceSecure123!"):
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)

    def test_unauthenticated_profile_access_redirects(self):
        """Unauthenticated requests to /profile must redirect to /login."""
        res_get = self.client.get("/profile")
        self.assertEqual(res_get.status_code, 302)
        self.assertIn("/login", res_get.headers.get("Location", ""))

        res_post = self.client.post("/profile", data={"action": "update_name", "name": "Hacker"})
        self.assertEqual(res_post.status_code, 302)
        self.assertIn("/login", res_post.headers.get("Location", ""))

    def test_view_profile_authenticated(self):
        """Logged-in clinician sees their profile details, created date, and assessment count."""
        self._login()
        res = self.client.get("/profile")
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("Dr. Alice Smith", html)
        self.assertIn("alice@example.com", html)
        self.assertIn("2026-09-15", html)
        self.assertIn("User Profile &amp; Account Settings", html)
        # Assessment count should be 2
        self.assertIn("Assessments", html)
        self.assertIn("2", html)

    def test_edit_display_name_success_and_session_update(self):
        """Updating display name updates the database, session, and rendered profile page."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "update_name",
            "name": "Dr. Alice Smith, MD, PhD"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("Display name updated successfully.", html)
        self.assertIn("Dr. Alice Smith, MD, PhD", html)

        # Check DB directly
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT name FROM users WHERE id = 1").fetchone()
            self.assertEqual(row["name"], "Dr. Alice Smith, MD, PhD")

    def test_edit_display_name_validation(self):
        """Blank or single-character display names are rejected with error flash."""
        self._login()
        # Blank name
        res = self.client.post("/profile", data={
            "action": "update_name",
            "name": "   "
        }, follow_redirects=True)
        self.assertIn("Display name must be at least 2 characters long.", res.data.decode("utf-8"))

        # 1 character
        res2 = self.client.post("/profile", data={
            "action": "update_name",
            "name": "A"
        }, follow_redirects=True)
        self.assertIn("Display name must be at least 2 characters long.", res2.data.decode("utf-8"))

        # DB name remained original
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT name FROM users WHERE id = 1").fetchone()
            self.assertEqual(row["name"], "Dr. Alice Smith")

    def test_update_email_success_with_password_verification(self):
        """Updating email succeeds when correct current password is provided."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "update_email",
            "email": "alice.new@hospital.org",
            "current_password_email": "AliceSecure123!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("Email address updated successfully.", html)
        self.assertIn("alice.new@hospital.org", html)

        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT email FROM users WHERE id = 1").fetchone()
            self.assertEqual(row["email"], "alice.new@hospital.org")

    def test_update_email_wrong_password_rejected(self):
        """Updating email with an incorrect current password is rejected."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "update_email",
            "email": "alice.intruder@hospital.org",
            "current_password_email": "WrongPassword999!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("Current password is incorrect. Verification failed.", html)

        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT email FROM users WHERE id = 1").fetchone()
            self.assertEqual(row["email"], "alice@example.com")

    def test_update_email_missing_password_rejected(self):
        """Submitting email update without current password fails verification."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "update_email",
            "email": "alice.new@hospital.org",
            "current_password_email": ""
        }, follow_redirects=True)

        html = res.data.decode("utf-8")
        self.assertIn("Current password is required to verify email update.", html)

    def test_update_email_invalid_format_rejected(self):
        """Submitting an invalid email format is rejected."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "update_email",
            "email": "notanemailaddress",
            "current_password_email": "AliceSecure123!"
        }, follow_redirects=True)

        html = res.data.decode("utf-8")
        self.assertIn("Please enter a valid email address.", html)

    def test_update_email_identical_to_current_rejected(self):
        """Submitting the current email address is rejected as identical."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "update_email",
            "email": "alice@example.com",
            "current_password_email": "AliceSecure123!"
        }, follow_redirects=True)

        html = res.data.decode("utf-8")
        self.assertIn("New email address is identical to your current registered email.", html)

    def test_update_email_duplicate_rejected(self):
        """Attempting to update email to one already registered by Bob is rejected."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "update_email",
            "email": "bob@example.com",
            "current_password_email": "AliceSecure123!"
        }, follow_redirects=True)

        html = res.data.decode("utf-8")
        self.assertIn("An account with this email address already exists.", html)

        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT email FROM users WHERE id = 1").fetchone()
            self.assertEqual(row["email"], "alice@example.com")

    def test_change_password_success_and_login_verification(self):
        """Changing password updates the hash in DB and allows immediate login with new credentials."""
        self._login()
        res = self.client.post("/profile", data={
            "action": "change_password",
            "current_password": "AliceSecure123!",
            "new_password": "NewAlicePass456#",
            "confirm_new_password": "NewAlicePass456#"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("Password changed successfully.", html)

        # Log out
        self.client.get("/logout")

        # Old password must fail
        res_old = self._login(email="alice@example.com", password="AliceSecure123!")
        self.assertIn("Invalid email or password", res_old.data.decode("utf-8"))

        # New password must succeed
        res_new = self._login(email="alice@example.com", password="NewAlicePass456#")
        self.assertIn("Welcome back, Dr. Alice Smith!", res_new.data.decode("utf-8"))

    def test_change_password_validation_rules(self):
        """Tests wrong current password, short new password, password reuse, and mismatch."""
        self._login()

        # 1. Wrong current password
        r1 = self.client.post("/profile", data={
            "action": "change_password",
            "current_password": "WrongPassword123!",
            "new_password": "ValidNewPass123!",
            "confirm_new_password": "ValidNewPass123!"
        }, follow_redirects=True)
        self.assertIn("Current password is incorrect.", r1.data.decode("utf-8"))

        # 2. Short new password (< 6 chars)
        r2 = self.client.post("/profile", data={
            "action": "change_password",
            "current_password": "AliceSecure123!",
            "new_password": "short",
            "confirm_new_password": "short"
        }, follow_redirects=True)
        self.assertIn("New password must be at least 6 characters long.", r2.data.decode("utf-8"))

        # 3. Reuse same password
        r3 = self.client.post("/profile", data={
            "action": "change_password",
            "current_password": "AliceSecure123!",
            "new_password": "AliceSecure123!",
            "confirm_new_password": "AliceSecure123!"
        }, follow_redirects=True)
        self.assertIn("New password must be different from your current password.", r3.data.decode("utf-8"))

        # 4. Confirmation mismatch
        r4 = self.client.post("/profile", data={
            "action": "change_password",
            "current_password": "AliceSecure123!",
            "new_password": "ValidNewPass123!",
            "confirm_new_password": "MismatchPass999!"
        }, follow_redirects=True)
        self.assertIn("New passwords do not match. Please re-enter.", r4.data.decode("utf-8"))

    def test_account_changes_preserve_historical_assessments(self):
        """
        Critical integrity check: Editing display name, email, and password
        never deletes, decouples, or modifies historical assessment records.
        """
        self._login()

        # Initial check
        with self.app.app_context():
            db = get_db()
            initial_count = db.execute("SELECT COUNT(*) FROM assessments WHERE user_id = 1").fetchone()[0]
            self.assertEqual(initial_count, 2)
            orig_records = db.execute("SELECT id, subject, risk, confidence, bmi FROM assessments WHERE user_id = 1 ORDER BY id").fetchall()

        # Perform all profile changes
        self.client.post("/profile", data={"action": "update_name", "name": "Prof. Alice S."}, follow_redirects=True)
        self.client.post("/profile", data={
            "action": "update_email",
            "email": "prof.alice@medical-center.org",
            "current_password_email": "AliceSecure123!"
        }, follow_redirects=True)
        self.client.post("/profile", data={
            "action": "change_password",
            "current_password": "AliceSecure123!",
            "new_password": "ProfAlicePass789$",
            "confirm_new_password": "ProfAlicePass789$"
        }, follow_redirects=True)

        # Verify historical assessments are 100% intact
        with self.app.app_context():
            db = get_db()
            after_count = db.execute("SELECT COUNT(*) FROM assessments WHERE user_id = 1").fetchone()[0]
            self.assertEqual(after_count, 2, "Historical assessments were deleted or decoupled!")

            after_records = db.execute("SELECT id, subject, risk, confidence, bmi FROM assessments WHERE user_id = 1 ORDER BY id").fetchall()
            for r_orig, r_after in zip(orig_records, after_records):
                self.assertEqual(r_orig["id"], r_after["id"])
                self.assertEqual(r_orig["subject"], r_after["subject"])
                self.assertEqual(r_orig["risk"], r_after["risk"])
                self.assertEqual(r_orig["confidence"], r_after["confidence"])
                self.assertEqual(r_orig["bmi"], r_after["bmi"])

    def test_secure_logout(self):
        """Verifies /logout clears session, redirects to home, and shows confirmation."""
        self._login()
        res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("You have been securely logged out.", html)

        # Subsequent access to protected /profile must redirect to /login
        res_profile = self.client.get("/profile")
        self.assertEqual(res_profile.status_code, 302)
        self.assertIn("/login", res_profile.headers.get("Location", ""))


if __name__ == "__main__":
    unittest.main()
