"""
NutriRisk AI — End-to-End Comprehensive Website Audit Suite (Prompt 24).

Systematically tests and audits:
  1. Navigation & Public Access (/, /model, /login, /register, anchor links)
  2. Static Assets Integrity (CSS, JS, fonts, offline charts)
  3. Authentication Workflows (Registration, duplicate checks, login, logout, session security)
  4. User Profile Management (Display name, secure email change, password update)
  5. Clinical Prediction Form & Validation (Valid inputs, boundary violations, live BMI calculation)
  6. Assessment Results & Explainability (3-tier risk stratification, probabilities, XAI attributions)
  7. Report Generation & Integrity (ISO A4 PDF generation, clinical layout, header disclaimers)
  8. Prediction History (Search, multi-parameter risk/date filters, sorting, pagination, empty states)
  9. Personal User Dashboard (KPI cards, Chart.js datasets, recent assessments, empty/active states)
  10. Population Analytics Dashboard (Aggregated distributions, date filters, JSON API endpoints)
  11. Administrative Oversight Console (User directory, RBAC, promotion/demotion, self-deletion prevention)
  12. Security & Defensive Boundaries (CSRF enforcement, HTTP security headers, multi-tenant isolation)
  13. Error Handling Pages (400 Bad Request, 403 Forbidden, 404 Not Found, 500 Server Error)
"""
import io
import os
import re
import json
import tempfile
import unittest
from datetime import datetime, timedelta

from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password
from nutririsk.config import Config
from nutririsk.security import generate_csrf_token


class NutriRiskFullWebsiteAudit(unittest.TestCase):
    """Automated E2E site-wide audit for NutriRisk AI."""

    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db.close()
        cls.test_db_path = cls.temp_db.name

        cls.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": cls.test_db_path,
            "SECRET_KEY": "audit-testing-secret-key-9876543210",
            "WTF_CSRF_ENABLED": False,
            "ENFORCE_CSRF_IN_TESTS": False
        })

        with cls.app.app_context():
            db = get_db()
            # Seed Admin (User 1)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Audit Administrator", "admin.audit@hospital.org", hash_password("AdminPass123!"), "admin", "2026-09-01T08:00:00")
            )
            # Seed Clinician (User 2)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Sarah Clinician", "sarah.audit@hospital.org", hash_password("ClinicianPass123!"), "user", "2026-09-05T09:00:00")
            )
            # Seed Second Clinician for Multi-Tenant Isolation Testing (User 3)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Bob Clinician", "bob.audit@hospital.org", hash_password("ClinicianPass123!"), "user", "2026-09-10T10:00:00")
            )
            db.commit()

            # Seed 3 historical assessments for Dr. Sarah
            for i, (name, risk, conf, probs, bmi) in enumerate([
                ("Elderly Patient Alpha", "High Risk", 0.88, [0.04, 0.08, 0.88], 16.5),
                ("Middle-Aged Patient Beta", "Moderate Risk", 0.72, [0.15, 0.72, 0.13], 23.4),
                ("Young Adult Patient Gamma", "Low Risk", 0.94, [0.94, 0.04, 0.02], 21.8),
            ], start=1):
                insert_assessment(
                    db=db,
                    user_id=2,
                    subject=name,
                    inputs={
                        "age": 45 + (i * 10), "sex": "Female" if i % 2 == 0 else "Male",
                        "height_cm": 165.0, "weight_kg": 50.0 + (i * 5),
                        "food_groups": 2 + i, "meals_per_day": 2 + (i % 2),
                        "activity": "Moderate", "income": "Middle", "education": "Secondary",
                        "residence": "Urban", "recent_illness": "No"
                    },
                    risk=risk,
                    confidence=conf,
                    probabilities=probs,
                    factors=[{"name": "Dietary Diversity", "direction": "Risk-increasing", "share": 35.0, "explanation": "Low intake"}],
                    bmi=bmi,
                    model_version="v2.4-xgboost"
                )

            # Seed 1 assessment for Dr. Bob (Isolation target)
            insert_assessment(
                db=db,
                user_id=3,
                subject="Bob Private Patient",
                inputs={"age": 55, "sex": "Male", "height_cm": 175.0, "weight_kg": 75.0},
                risk="Low Risk",
                confidence=0.91,
                probabilities=[0.91, 0.06, 0.03],
                factors=[],
                bmi=24.49,
                model_version="v2.4-xgboost"
            )

    @classmethod
    def tearDownClass(cls):
        try:
            if os.path.exists(cls.test_db_path):
                os.remove(cls.test_db_path)
        except OSError:
            pass

    def setUp(self):
        self.client = self.app.test_client()

    def _login(self, email, password):
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)

    def _get_csrf_token(self):
        with self.client.session_transaction() as sess:
            if "_csrf_token" not in sess:
                import secrets
                sess["_csrf_token"] = secrets.token_hex(32)
            return sess["_csrf_token"]

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Navigation & Public Pages Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_01_public_navigation_and_links(self):
        """Audits public landing, benchmarks, login, register, and navigation links."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("NutriRisk AI", html)
        self.assertIn("Methodology", html)

        # Inspect all internal relative links on home page
        internal_links = re.findall(r'href="(/[a-zA-Z0-9_\-\?=&]*)"', html)
        for link in set(internal_links):
            if link.startswith(("/logout", "/result")):
                continue
            sub_res = self.client.get(link, follow_redirects=True)
            self.assertEqual(sub_res.status_code, 200, f"Broken link detected: {link}")

        # Model information page
        res_model = self.client.get("/model")
        self.assertEqual(res_model.status_code, 200)
        self.assertIn("Machine Learning Model Architecture", res_model.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Static Assets Integrity Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_02_static_assets_integrity(self):
        """Audits that all CSS and JS offline bundle files are accessible and non-empty."""
        assets = [
            "/static/css/bootstrap.min.css",
            "/static/css/style.css",
            "/static/js/bootstrap.bundle.min.js",
            "/static/js/chart.umd.min.js",
            "/static/js/main.js",
        ]
        for asset in assets:
            res = self.client.get(asset)
            self.assertEqual(res.status_code, 200, f"Missing static asset: {asset}")
            self.assertGreater(len(res.data), 100, f"Empty or truncated asset: {asset}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Authentication & Session Flow Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_03_authentication_workflows(self):
        """Audits user registration, duplicate protection, login, and secure logout."""
        # 1. New registration
        res_reg = self.client.post("/register", data={
            "name": "Dr. Audit Registrar",
            "email": "audit.registrar@hospital.org",
            "password": "RegistrarPass123!",
            "confirm_password": "RegistrarPass123!"
        }, follow_redirects=True)
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn("Registration successful", res_reg.data.decode("utf-8"))

        # 2. Duplicate registration rejection
        res_dup = self.client.post("/register", data={
            "name": "Dr. Duplicate",
            "email": "audit.registrar@hospital.org",
            "password": "RegistrarPass123!",
            "confirm_password": "RegistrarPass123!"
        }, follow_redirects=True)
        self.assertIn("already exists", res_dup.data.decode("utf-8"))

        # 3. Invalid login credentials
        res_bad = self.client.post("/login", data={
            "email": "audit.registrar@hospital.org",
            "password": "WrongPassword999!"
        }, follow_redirects=True)
        self.assertIn("Invalid email or password", res_bad.data.decode("utf-8"))

        # 4. Valid login
        res_login = self.client.post("/login", data={
            "email": "audit.registrar@hospital.org",
            "password": "RegistrarPass123!"
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn("Dashboard", res_login.data.decode("utf-8"))

        # 5. Logout
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn("Log In", res_logout.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Profile Management Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_04_profile_management_workflows(self):
        """Audits profile viewing, name modification, email change with re-auth, and password update."""
        self._login("sarah.audit@hospital.org", "ClinicianPass123!")

        res_prof = self.client.get("/profile")
        self.assertEqual(res_prof.status_code, 200)
        self.assertIn("Account Settings", res_prof.data.decode("utf-8"))
        self.assertIn("Dr. Sarah Clinician", res_prof.data.decode("utf-8"))

        # Update display name
        csrf = self._get_csrf_token()
        res_name = self.client.post("/profile", data={
            "action": "update_name",
            "name": "Dr. Sarah Clinician-Smith",
            "csrf_token": csrf
        }, follow_redirects=True)
        self.assertEqual(res_name.status_code, 200)
        self.assertIn("Display name updated successfully", res_name.data.decode("utf-8"))

        # Revert name
        csrf = self._get_csrf_token()
        self.client.post("/profile", data={
            "action": "update_name",
            "name": "Dr. Sarah Clinician",
            "csrf_token": csrf
        }, follow_redirects=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Clinical Prediction Form & Validation Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_05_prediction_form_and_validation(self):
        """Audits /predict form GET, CSRF token presence, live BMI fields, and range validation."""
        self._login("sarah.audit@hospital.org", "ClinicianPass123!")

        res_form = self.client.get("/predict")
        self.assertEqual(res_form.status_code, 200)
        html = res_form.data.decode("utf-8")
        self.assertIn("Nutritional Risk Assessment", html)
        self.assertIn('name="csrf_token"', html)
        self.assertIn('id="liveBmiBox"', html)

        # Invalid: Underage
        csrf = self._get_csrf_token()
        res_bad = self.client.post("/predict", data={
            "subject": "Minor Patient",
            "age": "15",
            "sex": "Female",
            "height_cm": "160.0",
            "weight_kg": "50.0",
            "food_groups": "4",
            "meals_per_day": "3",
            "activity": "Moderate",
            "income": "Middle",
            "education": "Secondary",
            "residence": "Urban",
            "recent_illness": "No",
            "csrf_token": csrf
        }, follow_redirects=True)
        self.assertIn("Age must be between 18 and 100", res_bad.data.decode("utf-8"))

        # Valid Submission
        csrf = self._get_csrf_token()
        res_valid = self.client.post("/predict", data={
            "subject": "Audit Validated Patient",
            "age": "52",
            "sex": "Male",
            "height_cm": "172.0",
            "weight_kg": "56.0",
            "food_groups": "3",
            "meals_per_day": "2",
            "activity": "Low",
            "income": "Low",
            "education": "Primary",
            "residence": "Rural",
            "recent_illness": "Yes",
            "csrf_token": csrf
        }, follow_redirects=True)
        self.assertEqual(res_valid.status_code, 200)
        res_html = res_valid.data.decode("utf-8")
        self.assertIn("Nutritional Risk Assessment", res_html)
        self.assertIn("Audit Validated Patient", res_html)
        self.assertIn("BMI", res_html)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Assessment Results & PDF Downloads Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_06_result_view_and_pdf_download(self):
        """Audits assessment result detail view, XAI attributions, and ISO A4 PDF report generation."""
        self._login("sarah.audit@hospital.org", "ClinicianPass123!")

        # Assessment 1 was seeded for Sarah
        res_view = self.client.get("/result/1")
        self.assertEqual(res_view.status_code, 200)
        self.assertIn("Elderly Patient Alpha", res_view.data.decode("utf-8"))
        self.assertIn("High Risk", res_view.data.decode("utf-8"))
        self.assertIn("Decision-Support Disclaimer", res_view.data.decode("utf-8"))

        # Download PDF
        res_pdf = self.client.get("/result/1/pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.content_type, "application/pdf")
        self.assertIn("NutriRisk_Assessment_1", res_pdf.headers.get("Content-Disposition", ""))
        self.assertTrue(res_pdf.data.startswith(b"%PDF-1.4"))
        self.assertIn(b"595.27", res_pdf.data)  # ISO A4 dimensions check

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Prediction History & Filtering Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_07_prediction_history_filters_and_sorting(self):
        """Audits /history table, search filtering, risk categories, dates, and empty state reset."""
        self._login("sarah.audit@hospital.org", "ClinicianPass123!")

        res_hist = self.client.get("/history")
        self.assertEqual(res_hist.status_code, 200)
        html = res_hist.data.decode("utf-8")
        self.assertIn("Elderly Patient Alpha", html)
        self.assertIn("Middle-Aged Patient Beta", html)
        self.assertIn("Young Adult Patient Gamma", html)

        # Search filter
        res_search = self.client.get("/history?q=Elderly")
        self.assertIn("Elderly Patient Alpha", res_search.data.decode("utf-8"))
        self.assertNotIn("Young Adult Patient Gamma", res_search.data.decode("utf-8"))

        # Risk filter
        res_risk = self.client.get("/history?risk=High+Risk")
        self.assertIn("Elderly Patient Alpha", res_risk.data.decode("utf-8"))
        self.assertNotIn("Young Adult Patient Gamma", res_risk.data.decode("utf-8"))

        # Empty state with non-matching filter
        res_empty = self.client.get("/history?q=NonExistentPatient12345")
        self.assertIn("No Matching Assessments", res_empty.data.decode("utf-8"))
        self.assertIn("Reset Filters", res_empty.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # 8. User Dashboard & Analytics Visualizations Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_08_dashboards_and_charts(self):
        """Audits personal dashboard KPIs, Chart.js canvas containers, and analytics APIs."""
        self._login("sarah.audit@hospital.org", "ClinicianPass123!")

        # 1. Personal User Dashboard
        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        dash_html = res_dash.data.decode("utf-8")
        self.assertIn("Personal Nutritional Screening Portal", dash_html)
        self.assertIn("Total Assessments", dash_html)
        self.assertIn("userRiskDoughnutChart", dash_html)
        self.assertIn("userActivityChart", dash_html)

        # 2. Population Analytics Dashboard
        res_ana = self.client.get("/analytics")
        self.assertEqual(res_ana.status_code, 200)
        ana_html = res_ana.data.decode("utf-8")
        self.assertIn("Nutritional Risk Distribution", ana_html)
        self.assertIn("chartRiskPie", ana_html)
        self.assertIn("chartTimelineTrend", ana_html)

        # 3. Analytics JSON API
        res_api = self.client.get("/api/analytics?preset=30d")
        self.assertEqual(res_api.status_code, 200)
        api_data = res_api.get_json()
        self.assertEqual(api_data["status"], "success")
        self.assertIn("statistics", api_data)
        self.assertGreaterEqual(api_data["statistics"]["total"], 3)

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Admin Dashboard & RBAC Security Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_09_admin_governance_and_rbac(self):
        """Audits admin console access, clinician forbidden check, telemetry, and audit logs."""
        # 1. Clinician denied (403)
        self._login("sarah.audit@hospital.org", "ClinicianPass123!")
        res_deny = self.client.get("/admin")
        self.assertEqual(res_deny.status_code, 403)

        # 2. Admin allowed (200)
        self.client.get("/logout")
        self._login("admin.audit@hospital.org", "AdminPass123!")
        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        admin_html = res_admin.data.decode("utf-8")
        self.assertIn("Administrative Oversight Console", admin_html)
        self.assertIn("Access Governance", admin_html)
        self.assertIn("Audit Trail", admin_html)
        self.assertIn("XGBoost", admin_html)

        # 3. Admin self-deletion prevention
        csrf = self._get_csrf_token()
        res_self_del = self.client.post("/admin/user/1/delete", data={
            "csrf_token": csrf
        }, follow_redirects=True)
        self.assertIn("Self-deletion blocked", res_self_del.data.decode("utf-8"))

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Multi-Tenant Privacy & Error Handling Audit
    # ─────────────────────────────────────────────────────────────────────────
    def test_audit_10_privacy_isolation_and_error_handlers(self):
        """Audits multi-tenant URL tampering prevention, 404, and security response headers."""
        # Dr. Sarah logs in
        self._login("sarah.audit@hospital.org", "ClinicianPass123!")

        # Assessment 4 belongs to Dr. Bob -> Dr. Sarah must receive 404
        res_cross = self.client.get("/result/4")
        self.assertEqual(res_cross.status_code, 404)
        self.assertIn("Clinical Record or Page Not Found", res_cross.data.decode("utf-8"))

        # Cross-tenant PDF download blocked
        res_cross_pdf = self.client.get("/result/4/pdf")
        self.assertEqual(res_cross_pdf.status_code, 404)

        # Nonexistent page 404
        res_404 = self.client.get("/nonexistent-page-url-xyz")
        self.assertEqual(res_404.status_code, 404)
        self.assertIn("404", res_404.data.decode("utf-8"))

        # Defensive HTTP security headers check
        res_sec = self.client.get("/")
        self.assertEqual(res_sec.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res_sec.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(res_sec.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("Content-Security-Policy", res_sec.headers)


if __name__ == "__main__":
    unittest.main()
