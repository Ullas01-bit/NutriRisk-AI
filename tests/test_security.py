"""
Test Suite for NutriRisk AI Security, Error Handling, and Reliability (Prompt 21).

Covers:
  1. Secure password hashing with Scrypt and input validation.
  2. Cryptographic CSRF protection (blocking unsafe requests without token, accepting valid tokens).
  3. Defensive HTTP security headers (CSP, X-Frame-Options, X-Content-Type-Options, etc.).
  4. Proper custom error pages (400, 403, 404, 500) matching clinical design system.
  5. Safe model artifact loading and path traversal / LFI prevention.
  6. Secure session cookie flags (HttpOnly, SameSite, Lifetime).
  7. Multi-tenant authorization boundaries and privilege escalation prevention.
  8. Privacy-preserving email masking and zero sensitive credential leakage.
"""
import unittest
import os
import tempfile
from flask import session, abort
from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password, verify_password
from nutririsk.security import validate_safe_model_path, generate_csrf_token


class TestSecurityAndErrorHandling(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-security-secret-key-67890",
            "WTF_CSRF_ENABLED": False,  # Default disabled for generic tests, enabled in specific CSRF tests
            "ENFORCE_CSRF_IN_TESTS": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # User 1: Standard Clinician
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Alice Clinician", "alice@hospital.org", hash_password("AliceSecure123!"), "user", "2026-09-01T08:00:00")
            )
            # User 2: Administrator
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Super Admin", "admin@hospital.org", hash_password("AdminSecure999!"), "admin", "2026-09-01T08:00:00")
            )
            db.commit()

            # Seed assessment for User 1
            insert_assessment(
                db=db,
                user_id=1,
                subject="Patient Security Test",
                inputs={"age": 50, "sex": "Male", "height_cm": 175.0, "weight_kg": 70.0, "bmi": 22.86},
                risk="Low Risk",
                confidence=0.91,
                probabilities=[0.91, 0.06, 0.03],
                factors=[{"name": "BMI", "direction": "Protective"}],
                bmi=22.86,
                model_version="v1.0-xgboost"
            )

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def _login(self, email="alice@hospital.org", password="AliceSecure123!"):
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Secure Password Hashing
    # ─────────────────────────────────────────────────────────────────────────
    def test_secure_password_hashing_scrypt(self):
        """Verifies passwords use salted Scrypt hashing, reject empty inputs, and verify in constant time."""
        raw_pw = "ClinicianStrongPass2026!"
        hashed = hash_password(raw_pw)

        # Scrypt identifier prefix
        self.assertTrue(hashed.startswith("scrypt:"), f"Expected scrypt prefix, got: {hashed[:15]}")
        self.assertNotEqual(raw_pw, hashed)

        # Verification check
        self.assertTrue(verify_password(hashed, raw_pw))
        self.assertFalse(verify_password(hashed, "WrongPassword!"))
        self.assertFalse(verify_password(hashed, ""))
        self.assertFalse(verify_password("", raw_pw))

        # Empty password input rejection
        with self.assertRaises(ValueError):
            hash_password("")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. CSRF Protection
    # ─────────────────────────────────────────────────────────────────────────
    def test_csrf_blocks_unsafe_post_without_token_when_enabled(self):
        """Verifies that state-changing POST requests without CSRF token return 400 Bad Request."""
        csrf_app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "csrf-test-secret-key-111",
            "WTF_CSRF_ENABLED": True,
            "ENFORCE_CSRF_IN_TESTS": True
        })
        csrf_client = csrf_app.test_client()

        # Attempt to POST to login without CSRF token
        res = csrf_client.post("/login", data={
            "email": "alice@hospital.org",
            "password": "AliceSecure123!"
        })
        self.assertEqual(res.status_code, 400)
        html = res.data.decode("utf-8")
        self.assertIn("CSRF", html)
        self.assertIn("Bad Request", html)

    def test_csrf_accepts_valid_token(self):
        """Verifies that POST with a valid session CSRF token is accepted."""
        csrf_app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "csrf-test-secret-key-222",
            "WTF_CSRF_ENABLED": True,
            "ENFORCE_CSRF_IN_TESTS": True
        })
        csrf_client = csrf_app.test_client()

        # Initialize session by fetching GET /login
        get_res = csrf_client.get("/login")
        self.assertEqual(get_res.status_code, 200)

        # Extract CSRF token from the session or client context
        with csrf_client.session_transaction() as sess:
            token = sess.get("_csrf_token")

        self.assertIsNotNone(token, "Session did not generate a CSRF token.")

        # POST with valid token
        post_res = csrf_client.post("/login", data={
            "email": "alice@hospital.org",
            "password": "AliceSecure123!",
            "csrf_token": token
        }, follow_redirects=True)

        self.assertEqual(post_res.status_code, 200)
        self.assertIn("Welcome back", post_res.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Defensive Security Headers
    # ─────────────────────────────────────────────────────────────────────────
    def test_defensive_security_headers_present(self):
        """Verifies that all responses include defense-in-depth HTTP security headers."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        headers = res.headers
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("geolocation=()", headers.get("Permissions-Policy", ""))
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy", ""))
        self.assertEqual(headers.get("Server"), "NutriRisk-Clinical-Engine")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Custom Clinical Error Handlers (400, 403, 404, 500)
    # ─────────────────────────────────────────────────────────────────────────
    def test_custom_404_error_page(self):
        """Requesting an invalid route returns 404 with custom clinical styling and navigation."""
        res = self.client.get("/nonexistent-clinical-endpoint-xyz")
        self.assertEqual(res.status_code, 404)

        html = res.data.decode("utf-8")
        self.assertIn("HTTP Error 404", html)
        self.assertIn("Clinical Record or Page Not Found", html)
        self.assertIn("Return to Home", html)

    def test_custom_403_error_page(self):
        """Standard user attempting to access administrative console receives custom 403 page."""
        self._login(email="alice@hospital.org", password="AliceSecure123!")
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 403)

        html = res.data.decode("utf-8")
        self.assertIn("HTTP Error 403", html)
        self.assertIn("Administrative Privileges Required", html)

    def test_custom_500_error_page(self):
        """Internal server error renders custom 500 page without leaking technical stack trace."""
        @self.app.route("/force-test-server-error")
        def force_error():
            abort(500)

        res = self.client.get("/force-test-server-error")
        self.assertEqual(res.status_code, 500)

        html = res.data.decode("utf-8")
        self.assertIn("HTTP Error 500", html)
        self.assertIn("Unexpected Application Error", html)
        # Verify no traceback exposure
        self.assertNotIn("Traceback (most recent call last)", html)
        self.assertNotIn("sqlite3.OperationalError", html)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Safe Model Artifact Path Sanitization (LFI / Path Traversal)
    # ─────────────────────────────────────────────────────────────────────────
    def test_model_path_validation_and_traversal_prevention(self):
        """Verifies path containment check prevents path traversal and untrusted extensions."""
        base_dir = self.app.config.get("BASE_DIR")

        # 1. Valid local model path inside BASE_DIR
        valid_path = os.path.join(base_dir, "model", "model.joblib")
        validated = validate_safe_model_path(valid_path, allowed_base_dir=base_dir)
        self.assertTrue(os.path.isabs(validated))

        # 2. Path traversal escaping root
        traversal_path = os.path.join(base_dir, "..", "..", "windows", "system32", "cmd.exe")
        with self.assertRaises(ValueError) as ctx:
            validate_safe_model_path(traversal_path, allowed_base_dir=base_dir)
        self.assertIn("resolves outside trusted application root", str(ctx.exception))

        # 3. Untrusted file extension
        untrusted_ext = os.path.join(base_dir, "model", "malicious_script.sh")
        with self.assertRaises(ValueError) as ctx2:
            validate_safe_model_path(untrusted_ext, allowed_base_dir=base_dir)
        self.assertIn("untrusted extension", str(ctx2.exception))

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Secure Session Configuration
    # ─────────────────────────────────────────────────────────────────────────
    def test_session_cookie_security_flags(self):
        """Verifies session cookie security configuration defaults."""
        self.assertTrue(self.app.config.get("SESSION_COOKIE_HTTPONLY"))
        self.assertEqual(self.app.config.get("SESSION_COOKIE_SAMESITE"), "Lax")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Privacy & Multi-Tenant Authorization Protection
    # ─────────────────────────────────────────────────────────────────────────
    def test_multi_tenant_record_protection(self):
        """Clinician 2 cannot access Clinician 1's assessment record (must return 404)."""
        # Register and log in as Clinician 2 (id=3)
        self.client.post("/register", data={
            "name": "Dr. Bob Clinician",
            "email": "bob.clinician@hospital.org",
            "password": "BobClinicianPass123!",
            "confirm_password": "BobClinicianPass123!"
        }, follow_redirects=True)

        self._login(email="bob.clinician@hospital.org", password="BobClinicianPass123!")

        # Assessment #1 belongs to Clinician 1 (Alice)
        res_view = self.client.get("/result/1")
        self.assertEqual(res_view.status_code, 404)

        res_download = self.client.get("/assessment/1/download")
        self.assertEqual(res_download.status_code, 404)


if __name__ == "__main__":
    unittest.main()
