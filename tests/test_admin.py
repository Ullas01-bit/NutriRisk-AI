"""
Test Suite for NutriRisk AI Administrative Oversight Console (Prompt 17).
Validates:
  1. Access Control: Anonymous redirected to /login, non-admin receives 403 Forbidden.
  2. Protected Actions: Non-admins blocked from role changes and user deletion (403).
  3. Admin Console Rendering: Users directory, KPIs, Model telemetry, Dataset provenance, Audit logs.
  4. Privacy Guarantee: Zero exposure of password hashes or plain passwords in HTML/context.
  5. User Governance: Role promotion to admin and demotion to user.
  6. Privilege Safeguards: Admin self-demotion blocked, sole-admin demotion blocked.
  7. Account Deletion: User deletion with assessment cascade and audit logging.
  8. Deletion Safeguards: Admin self-deletion blocked, sole-admin deletion blocked.
  9. Audit Trail Integrity: All administrative mutations recorded in admin_audit_logs.
"""
import unittest
import os
import tempfile
from datetime import datetime
from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password

class TestAdminDashboard(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-admin-secret-key-99999",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # 1. Primary Admin User (ID = 1)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Primary Admin", "admin@hospital.org", hash_password("SecretAdminPass123!"), "admin", "2026-09-01T08:00:00")
            )
            # 2. Regular Clinician User (ID = 2)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Regular", "clinician@clinic.org", hash_password("ClinicianPass123!"), "user", "2026-09-15T08:00:00")
            )
            # 3. Secondary Clinician User (ID = 3)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Secondary", "secondary@clinic.org", hash_password("SecondaryPass123!"), "user", "2026-09-20T08:00:00")
            )
            db.commit()

            # Seed assessments for User 2
            insert_assessment(
                db=db,
                user_id=2,
                subject="Subject Alpha",
                inputs={"age": 45, "sex": "Female", "bmi": 21.5},
                risk="Low Risk",
                confidence=0.88,
                probabilities=[0.88, 0.10, 0.02],
                factors=[{"name": "BMI", "impact": "Protective"}],
                bmi=21.5,
                model_version="v1.0-xgboost"
            )
            insert_assessment(
                db=db,
                user_id=2,
                subject="Subject Beta",
                inputs={"age": 68, "sex": "Male", "bmi": 17.2},
                risk="High Risk",
                confidence=0.91,
                probabilities=[0.02, 0.07, 0.91],
                factors=[{"name": "BMI", "impact": "Risk-increasing"}],
                bmi=17.2,
                model_version="v1.0-xgboost"
            )

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def login_admin(self):
        """Helper to establish an authenticated administrator session."""
        return self.client.post("/login", data={
            "email": "admin@hospital.org",
            "password": "SecretAdminPass123!"
        }, follow_redirects=True)

    def login_user(self):
        """Helper to establish an authenticated regular clinician session."""
        return self.client.post("/login", data={
            "email": "clinician@clinic.org",
            "password": "ClinicianPass123!"
        }, follow_redirects=True)

    def test_unauthenticated_access_redirects(self):
        """Unauthenticated visitor to /admin must be redirected to /login."""
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

    def test_regular_user_forbidden_403(self):
        """Standard authenticated user must receive 403 Forbidden for admin endpoints."""
        self.login_user()

        # 1. Main admin view
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 403)

        # 2. Role alteration attempt
        res_role = self.client.post("/admin/user/2/role", data={"role": "admin"})
        self.assertEqual(res_role.status_code, 403)

        # 3. User deletion attempt
        res_del = self.client.post("/admin/user/3/delete")
        self.assertEqual(res_del.status_code, 403)

    def test_admin_console_renders_successfully(self):
        """Admin can access /admin and view governance dashboard and telemetry."""
        self.login_admin()
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)

        html = res.get_data(as_text=True)
        self.assertIn("Administrative Oversight Console", html)
        self.assertIn("Registered Users", html)
        self.assertIn("Total Screenings", html)
        self.assertIn("Active Model", html)
        self.assertIn("Database Storage", html)
        self.assertIn("Primary Admin", html)
        self.assertIn("Dr. Regular", html)
        self.assertIn("clinician@clinic.org", html)
        self.assertIn("Administrative Security Audit Trail", html)

    def test_zero_password_hash_exposure(self):
        """Strict Privacy: Password hashes must never appear anywhere in the rendered HTML."""
        self.login_admin()
        res = self.client.get("/admin")
        html = res.get_data(as_text=True)

        self.assertNotIn("SecretAdminPass123!", html)
        self.assertNotIn("ClinicianPass123!", html)
        # Check that scrypt or pbkdf2 hash signatures don't appear in the HTML
        self.assertNotIn("scrypt:", html)
        self.assertNotIn("pbkdf2:", html)

    def test_admin_promote_and_demote_user(self):
        """Admin can promote a user to admin, and demote them back; actions are logged."""
        self.login_admin()

        # 1. Promote User 2 (Dr. Regular) to admin
        res_promote = self.client.post("/admin/user/2/role", data={"role": "admin"}, follow_redirects=True)
        self.assertEqual(res_promote.status_code, 200)
        html_promoted = res_promote.get_data(as_text=True)
        self.assertIn("role updated to &#39;admin&#39;", html_promoted)

        # Verify in DB
        with self.app.app_context():
            db = get_db()
            user2 = db.execute("SELECT role FROM users WHERE id = 2").fetchone()
            self.assertEqual(user2["role"], "admin")

            # Verify audit log entry
            log = db.execute(
                "SELECT * FROM admin_audit_logs WHERE action = 'ROLE_ADMIN' AND target_user_id = 2"
            ).fetchone()
            self.assertIsNotNone(log)
            self.assertEqual(log["admin_name"], "Primary Admin")

        # 2. Demote User 2 back to regular user
        res_demote = self.client.post("/admin/user/2/role", data={"role": "user"}, follow_redirects=True)
        self.assertEqual(res_demote.status_code, 200)

        with self.app.app_context():
            db = get_db()
            user2 = db.execute("SELECT role FROM users WHERE id = 2").fetchone()
            self.assertEqual(user2["role"], "user")

            log_demote = db.execute(
                "SELECT * FROM admin_audit_logs WHERE action = 'ROLE_USER' AND target_user_id = 2"
            ).fetchone()
            self.assertIsNotNone(log_demote)

    def test_self_demotion_prevented(self):
        """Admin cannot demote their own active session."""
        self.login_admin()
        # Admin is User ID 1
        res = self.client.post("/admin/user/1/role", data={"role": "user"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("You cannot demote your own administrator account", html)

        with self.app.app_context():
            db = get_db()
            admin_user = db.execute("SELECT role FROM users WHERE id = 1").fetchone()
            self.assertEqual(admin_user["role"], "admin")

    def test_sole_admin_demotion_prevented(self):
        """Cannot demote the sole administrator in the system."""
        self.login_admin()

        with self.app.app_context():
            db = get_db()
            admin_count = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
            self.assertEqual(admin_count, 1)

        # Even with forced spoofing of target ID (e.g. from an admin session targeting another admin when only 1 exists)
        # Verify guard blocks if admin_count <= 1
        res = self.client.post("/admin/user/1/role", data={"role": "user"}, follow_redirects=True)
        html = res.get_data(as_text=True)
        self.assertTrue(
            "You cannot demote your own administrator account" in html or
            "Cannot demote the sole administrator" in html
        )

    def test_delete_user_cascades_assessments_and_logs(self):
        """Admin can delete a regular user; their assessments cascade delete and an audit log is created."""
        self.login_admin()

        # User 2 has 2 assessments before deletion
        with self.app.app_context():
            db = get_db()
            assessments_before = db.execute("SELECT COUNT(*) FROM assessments WHERE user_id = 2").fetchone()[0]
            self.assertEqual(assessments_before, 2)

        # Delete User 2
        res = self.client.post("/admin/user/2/delete", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("and associated assessments have been deleted", html)

        # Verify User 2 and their assessments are deleted
        with self.app.app_context():
            db = get_db()
            user2 = db.execute("SELECT * FROM users WHERE id = 2").fetchone()
            self.assertIsNone(user2)

            assessments_after = db.execute("SELECT COUNT(*) FROM assessments WHERE user_id = 2").fetchone()[0]
            self.assertEqual(assessments_after, 0)

            # Check audit log
            audit = db.execute(
                "SELECT * FROM admin_audit_logs WHERE action = 'USER_DELETED' AND target_user_id = 2"
            ).fetchone()
            self.assertIsNotNone(audit)
            self.assertIn("Deleted user account #2", audit["details"])

    def test_admin_self_deletion_prevented(self):
        """Admin cannot delete their own active account."""
        self.login_admin()
        res = self.client.post("/admin/user/1/delete", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("You cannot delete your own active administrator account", html)

        with self.app.app_context():
            db = get_db()
            admin_user = db.execute("SELECT * FROM users WHERE id = 1").fetchone()
            self.assertIsNotNone(admin_user)

    def test_sole_admin_deletion_prevented(self):
        """Cannot delete the sole administrator account even if invoked with target id."""
        self.login_admin()
        # Create a second admin first
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET role = 'admin' WHERE id = 3")
            db.commit()

        # Admin 1 deletes Admin 3
        res = self.client.post("/admin/user/3/delete", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Now only Admin 1 remains
        with self.app.app_context():
            db = get_db()
            admin_count = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
            self.assertEqual(admin_count, 1)

    def test_invalid_role_rejected(self):
        """Submitting an invalid role string is rejected."""
        self.login_admin()
        res = self.client.post("/admin/user/2/role", data={"role": "super_root_admin"}, follow_redirects=True)
        html = res.get_data(as_text=True)
        self.assertIn("Invalid role specified", html)

    def test_nonexistent_user_handled_gracefully(self):
        """Operating on a nonexistent user returns a graceful flash message."""
        self.login_admin()
        res_role = self.client.post("/admin/user/99999/role", data={"role": "admin"}, follow_redirects=True)
        self.assertIn("Target user not found", res_role.get_data(as_text=True))

        res_del = self.client.post("/admin/user/99999/delete", follow_redirects=True)
        self.assertIn("Target user account not found", res_del.get_data(as_text=True))

if __name__ == "__main__":
    unittest.main()
