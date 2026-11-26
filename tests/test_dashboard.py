"""
Test Suite for NutriRisk AI User Dashboard (Prompt 14).
Validates user dashboard with 0, 1, and multiple assessments,
empty states, profile summaries, risk distributions, and multi-tenant isolation.
"""
import unittest
import os
import json
import tempfile
from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password

class TestUserDashboard(unittest.TestCase):
    def setUp(self):
        # Create unique temp database file for each test method
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-dashboard-secret-key-12345",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # Create User A (Primary Test User)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Alice Walker", "alice@example.com", hash_password("alice123"), "user", "2026-10-01T09:00:00")
            )
            # Create User B (To test multi-tenant isolation)
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Bob Smith", "bob@example.com", hash_password("bob123"), "user", "2026-10-02T10:00:00")
            )
            db.commit()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def login_alice(self):
        return self.client.post("/login", data={
            "email": "alice@example.com",
            "password": "alice123"
        }, follow_redirects=True)

    def login_bob(self):
        return self.client.post("/login", data={
            "email": "bob@example.com",
            "password": "bob123"
        }, follow_redirects=True)

    def test_unauthenticated_dashboard_redirects(self):
        """Unauthenticated access to /dashboard must redirect to /login."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_dashboard_with_zero_assessments(self):
        """A new user with 0 assessments sees welcome banner, empty state, and 0 total count."""
        self.login_alice()
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        
        # Welcome message & Profile summary
        self.assertIn(b"Welcome back, Dr. Alice Walker", response.data)
        self.assertIn(b"alice@example.com", response.data)
        self.assertIn(b"Member since 2026-10-01", response.data)

        # Empty state & Action buttons
        self.assertIn(b"Welcome to your NutriRisk AI Dashboard!", response.data)
        self.assertIn(b"You have not recorded any nutritional risk assessments yet", response.data)
        self.assertIn(b"Start Your First Assessment", response.data)
        self.assertIn(b"Quick Start Assessment", response.data)
        self.assertIn(b"View History", response.data)

        # Longitudinal disclaimer present
        self.assertIn(b"Clinical Longitudinal Decision-Support Guidance", response.data)
        self.assertIn(b"do NOT constitute proof of clinical recovery", response.data)

        # Chart canvases should not be rendered in empty state
        self.assertNotIn(b'id="userRiskDoughnutChart"', response.data)
        self.assertNotIn(b'id="userActivityChart"', response.data)

    def test_dashboard_with_one_assessment(self):
        """User with exactly 1 assessment sees KPIs, latest risk category, and chart data."""
        with self.app.app_context():
            db = get_db()
            aid = insert_assessment(
                db=db,
                user_id=1,  # Alice
                subject="Patient Baseline - Jane Doe",
                inputs={"age": 45, "sex": "Female", "height_cm": 165.0, "weight_kg": 60.0},
                risk="Low Risk",
                confidence=0.885,
                probabilities={"Low Risk": 0.885, "Moderate Risk": 0.095, "High Risk": 0.02},
                factors=[{"feature": "Dietary Diversity", "impact": "Protective"}],
                bmi=22.04,
                model_version="v1.0-xgboost"
            )

        self.login_alice()
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

        # Total count = 1
        self.assertIn(b"Total Assessments", response.data)
        self.assertIn(b"Patient Baseline - Jane Doe", response.data)
        self.assertIn(b"Low Risk", response.data)
        self.assertIn(b"88.5%", response.data)
        self.assertIn(b"22.0", response.data)

        # Chart canvases rendered
        self.assertIn(b'id="userRiskDoughnutChart"', response.data)
        self.assertIn(b'id="userActivityChart"', response.data)

        # Recent assessment table entry
        self.assertIn(f"#{aid}".encode(), response.data)
        self.assertIn(b"View", response.data)
        self.assertIn(b"PDF", response.data)

        # Empty state should NOT be rendered
        self.assertNotIn(b"You have not recorded any nutritional risk assessments yet", response.data)

    def test_dashboard_with_multiple_assessments_and_isolation(self):
        """User with multiple assessments sees distribution breakdown, and cannot see other users' data."""
        with self.app.app_context():
            db = get_db()
            # Alice's 3 assessments across all 3 tiers
            insert_assessment(
                db=db, user_id=1, subject="Alice Case 1",
                inputs={"age": 28, "sex": "Male", "height_cm": 175.0, "weight_kg": 72.0},
                risk="Low Risk", confidence=0.85, probabilities={"Low Risk": 0.85, "Moderate Risk": 0.1, "High Risk": 0.05},
                factors=[], bmi=23.51
            )
            insert_assessment(
                db=db, user_id=1, subject="Alice Case 2",
                inputs={"age": 62, "sex": "Female", "height_cm": 158.0, "weight_kg": 44.0},
                risk="Moderate Risk", confidence=0.72, probabilities={"Low Risk": 0.18, "Moderate Risk": 0.72, "High Risk": 0.1},
                factors=[], bmi=17.62
            )
            insert_assessment(
                db=db, user_id=1, subject="Alice Case 3",
                inputs={"age": 79, "sex": "Female", "height_cm": 150.0, "weight_kg": 35.0},
                risk="High Risk", confidence=0.91, probabilities={"Low Risk": 0.02, "Moderate Risk": 0.07, "High Risk": 0.91},
                factors=[], bmi=15.56
            )

            # Bob's 1 assessment (Should NOT appear on Alice's dashboard)
            insert_assessment(
                db=db, user_id=2, subject="Bob Secret Patient",
                inputs={"age": 50, "sex": "Male", "height_cm": 180.0, "weight_kg": 85.0},
                risk="High Risk", confidence=0.99, probabilities={"Low Risk": 0.0, "Moderate Risk": 0.01, "High Risk": 0.99},
                factors=[], bmi=26.23
            )

        # 1. Verify Alice's Dashboard
        self.login_alice()
        r_alice = self.client.get("/dashboard")
        self.assertEqual(r_alice.status_code, 200)

        # Total count for Alice should be 3 (not 4)
        self.assertIn(b"Total Assessments", r_alice.data)
        self.assertIn(b">3</div>", r_alice.data)

        # Alice's subjects are present
        self.assertIn(b"Alice Case 1", r_alice.data)
        self.assertIn(b"Alice Case 2", r_alice.data)
        self.assertIn(b"Alice Case 3", r_alice.data)

        # Bob's subject MUST NOT be present on Alice's dashboard
        self.assertNotIn(b"Bob Secret Patient", r_alice.data)

        # Check latest is Alice Case 3 (High Risk, 91.0%)
        self.assertIn(b"Alice Case 3", r_alice.data)
        self.assertIn(b"91.0%", r_alice.data)

        # 2. Verify Bob's Dashboard
        self.login_bob()
        r_bob = self.client.get("/dashboard")
        self.assertEqual(r_bob.status_code, 200)
        self.assertIn(b"Welcome back, Dr. Bob Smith", r_bob.data)
        self.assertIn(b">1</div>", r_bob.data)
        self.assertIn(b"Bob Secret Patient", r_bob.data)
        self.assertNotIn(b"Alice Case 1", r_bob.data)

if __name__ == "__main__":
    unittest.main()
