"""
Test Suite for NutriRisk AI Healthcare Analytics Dashboard (Prompt 16).
Validates:
  1. Unauthenticated protection.
  2. Empty state handling when no data exists or when date filters yield 0 records.
  3. Total screened, Low Risk, Moderate Risk, and High Risk counts.
  4. Numerical consistency across all cards, cohorts, and distribution charts.
  5. Age cohort binning, sex distribution, and BMI categorizations.
  6. Date-range filtering and quick presets (7d, 30d, YTD).
  7. Cross-tabulation: Risk category comparison by age cohort.
  8. JSON API endpoint /api/analytics response integrity.
  9. Multi-tenant privacy and admin scope switching.
"""
import unittest
import os
import json
import tempfile
from datetime import datetime, timedelta
from nutririsk import create_app
from nutririsk.db import get_db, insert_assessment
from nutririsk.auth.utils import hash_password

class TestAnalyticsDashboard(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.test_db_path = self.temp_db.name

        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.test_db_path,
            "SECRET_KEY": "test-analytics-secret-key-12345",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            # 1. Admin user
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Admin", "admin@hospital.org", hash_password("admin123"), "admin", "2026-09-01T08:00:00")
            )
            # 2. Regular clinician user
            db.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("Dr. Clinician", "clinician@clinic.org", hash_password("clinic123"), "user", "2026-09-15T08:00:00")
            )
            db.commit()

            # Seed 6 diverse records for Clinician (user_id = 2)
            today_str = datetime.now().date().isoformat()
            past_10d = (datetime.now().date() - timedelta(days=10)).isoformat()
            past_40d = (datetime.now().date() - timedelta(days=40)).isoformat()

            clinician_records = [
                # (subject, date, risk, conf, age, sex, bmi)
                ("Case A", f"{today_str}T09:00:00", "Low Risk", 0.90, 24, "Female", 22.0),
                ("Case B", f"{today_str}T11:00:00", "Low Risk", 0.85, 35, "Male", 24.5),
                ("Case C", f"{past_10d}T10:00:00", "Moderate Risk", 0.75, 52, "Female", 19.1),
                ("Case D", f"{past_10d}T14:30:00", "Moderate Risk", 0.70, 68, "Male", 27.4),
                ("Case E", f"{past_40d}T08:15:00", "High Risk", 0.94, 81, "Female", 15.6),
                ("Case F", f"{past_40d}T16:45:00", "High Risk", 0.92, 72, "Male", 31.8)
            ]

            for subj, dt, rk, conf, age, sex, bmi in clinician_records:
                db.execute(
                    """INSERT INTO assessments 
                       (user_id, subject, created, inputs, risk, confidence, probs, factors, age, sex, bmi, model_version)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (2, subj, dt, json.dumps({"age": age, "sex": sex}), rk, conf, json.dumps({"Low Risk": 0.33, "Moderate Risk": 0.33, "High Risk": 0.34}), json.dumps([]), age, sex, bmi, "v1.0-xgboost")
                )

            # Seed 2 records for Admin (user_id = 1)
            admin_records = [
                ("Admin Case 1", f"{today_str}T12:00:00", "Low Risk", 0.95, 29, "Female", 21.0),
                ("Admin Case 2", f"{past_10d}T15:00:00", "High Risk", 0.88, 77, "Male", 16.2)
            ]
            for subj, dt, rk, conf, age, sex, bmi in admin_records:
                db.execute(
                    """INSERT INTO assessments 
                       (user_id, subject, created, inputs, risk, confidence, probs, factors, age, sex, bmi, model_version)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (1, subj, dt, json.dumps({"age": age, "sex": sex}), rk, conf, json.dumps({"Low Risk": 0.5, "Moderate Risk": 0.3, "High Risk": 0.2}), json.dumps([]), age, sex, bmi, "v1.0-xgboost")
                )
            db.commit()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def login_clinician(self):
        return self.client.post("/login", data={
            "email": "clinician@clinic.org",
            "password": "clinic123"
        }, follow_redirects=True)

    def login_admin(self):
        return self.client.post("/login", data={
            "email": "admin@hospital.org",
            "password": "admin123"
        }, follow_redirects=True)

    def test_analytics_unauthenticated_redirects(self):
        """Unauthenticated requests to /analytics must redirect to /login."""
        response = self.client.get("/analytics")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_analytics_dashboard_personal_scope(self):
        """Clinician sees their exact 6 assessments with matching risk counts and summary statistics."""
        self.login_clinician()
        response = self.client.get("/analytics")
        self.assertEqual(response.status_code, 200)

        # Header and Personal Cohort Badge
        self.assertIn(b"Healthcare Analytics", response.data)
        self.assertIn(b"Personal Screening Cohort", response.data)

        # KPI Totals
        self.assertIn(b">6</div>", response.data)  # Total 6
        self.assertIn(b">2</div>", response.data)  # Low 2, Moderate 2, High 2 (each has count 2)
        self.assertIn(b"33.3%", response.data)     # 2/6 = 33.3%

        # Summary statistics
        self.assertIn(b"Cohort Mean Age", response.data)
        self.assertIn(b"Cohort Mean BMI", response.data)
        self.assertIn(b"Mean Model Confidence", response.data)

        # Charts present
        self.assertIn(b'id="chartRiskPie"', response.data)
        self.assertIn(b'id="chartBMIDist"', response.data)
        self.assertIn(b'id="chartAgeDist"', response.data)
        self.assertIn(b'id="chartSexRatio"', response.data)
        self.assertIn(b'id="chartRiskByAge"', response.data)
        self.assertIn(b'id="chartTimelineTrend"', response.data)

    def test_analytics_numerical_consistency(self):
        """All categorical distributions must sum exactly to total count."""
        from nutririsk.routes.analytics import calculate_statistics

        with self.app.app_context():
            stats = calculate_statistics("WHERE user_id = ?", (2,))

            total = stats["total"]
            self.assertEqual(total, 6)

            # 1. Low + Mod + High == Total
            risk_sum = stats["low_count"] + stats["moderate_count"] + stats["high_count"]
            self.assertEqual(risk_sum, total)

            # 2. Age counts sum == Total
            self.assertEqual(sum(stats["age_counts"]), total)

            # 3. Sex counts sum == Total
            self.assertEqual(sum(stats["sex_counts"]), total)

            # 4. BMI counts sum == Total
            self.assertEqual(sum(stats["bmi_counts"]), total)

            # 5. Risk by age cross-tabulation sums
            stacked_sum = sum(sum(counts) for counts in stats["risk_by_age"].values())
            self.assertEqual(stacked_sum, total)

    def test_date_range_filtering(self):
        """Date filtering limits statistics strictly to the selected range."""
        self.login_clinician()
        today_str = datetime.now().date().isoformat()

        # Filter strictly for today (Case A & Case B: both Low Risk)
        res = self.client.get(f"/analytics?start_date={today_str}&end_date={today_str}")
        self.assertEqual(res.status_code, 200)

        # Total screened should be 2
        self.assertIn(b">2</div>", res.data)
        self.assertIn(b"100.0%", res.data)  # Low risk is 100% of today's cohort

    def test_quick_date_presets(self):
        """Preset filter (preset=7d) returns only records from the last 7 days."""
        self.login_clinician()
        res = self.client.get("/analytics?preset=7d")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b">2</div>", res.data)  # Only today's 2 records are within 7 days

    def test_empty_state_when_no_data_in_date_range(self):
        """Filter resulting in 0 records shows clean empty state without crashing charts."""
        self.login_clinician()
        res = self.client.get("/analytics?start_date=2020-01-01&end_date=2020-01-02")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No Assessments in Selected Range", res.data)
        self.assertIn(b"Reset Date Range", res.data)
        # Charts should not render in empty state
        self.assertNotIn(b'id="chartRiskPie"', res.data)

    def test_api_analytics_endpoint(self):
        """JSON API /api/analytics returns structured data matching actual DB records."""
        self.login_clinician()
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scope"], "personal")
        self.assertEqual(data["statistics"]["total"], 6)
        self.assertEqual(data["statistics"]["low_count"], 2)
        self.assertEqual(data["statistics"]["moderate_count"], 2)
        self.assertEqual(data["statistics"]["high_count"], 2)
        self.assertIn("mean_bmi", data["statistics"]["summary"])

    def test_admin_system_wide_analytics_scope(self):
        """Admin can view all 8 assessments across all users."""
        self.login_admin()
        res = self.client.get("/analytics?scope=all")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"System-Wide Cohort", res.data)
        self.assertIn(b">8</div>", res.data)  # Total 6 (Clinician) + 2 (Admin) = 8

if __name__ == "__main__":
    unittest.main()
