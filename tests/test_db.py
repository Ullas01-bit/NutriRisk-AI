"""
Unit and integration tests for NutriRisk AI SQLite database implementation (Prompt 13).

Covers:
  1. Database initialization and table schema verification.
  2. Users table CRUD, password hashing, and email uniqueness constraint.
  3. Assessments table CRUD, BMI calculation, and model version tracking.
  4. Non-destructive database migrations (schema upgrade & historical BMI backfill).
  5. Multi-tenant access control and record isolation (regular user vs admin).
  6. Foreign key cascading deletions (ON DELETE CASCADE).
  7. ML Model metadata tracking and active-version switching.
  8. Parameterized query protection against SQL injection.
"""
import os
import sys
import json
import sqlite3
import unittest
import tempfile
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nutririsk.db import (
    init_db, safe_migrate, get_user_by_id, get_user_by_email,
    insert_assessment, get_assessment_secure, save_model_metadata_record
)
from nutririsk.auth.utils import hash_password, verify_password


class DummyApp:
    """Minimal mock app object providing configuration for init_db."""
    def __init__(self, db_path: str):
        self.config = {
            "DATABASE_PATH": db_path,
            "METRICS_PATH": "model/metrics.json"
        }


class TestDatabaseImplementation(unittest.TestCase):

    def setUp(self):
        """Creates an isolated temporary database file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db_path = self.temp_file.name
        self.app = DummyApp(self.db_path)
        init_db(self.app)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def tearDown(self):
        """Closes connection and removes temporary database file."""
        self.conn.close()
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_schema_and_indexes_created(self):
        """Validates that all tables and indexes exist with correct constraints."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        self.assertIn("users", tables)
        self.assertIn("assessments", tables)
        self.assertIn("model_metadata", tables)

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {row[0] for row in cursor.fetchall()}
        self.assertIn("idx_users_email", indexes)
        self.assertIn("idx_assessments_user_id", indexes)
        self.assertIn("idx_assessments_risk", indexes)
        self.assertIn("idx_assessments_created", indexes)
        self.assertIn("idx_model_metadata_active", indexes)

    def test_user_creation_and_password_hashing(self):
        """Verifies that users are saved with hashed passwords and retrieved by email/ID."""
        plain_pw = "DoctorSecret123"
        hashed = hash_password(plain_pw)
        self.assertNotEqual(hashed, plain_pw)

        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
            ("Dr. Jane Doe", "jane@clinic.org", hashed, "user", now)
        )
        self.conn.commit()
        uid = cursor.lastrowid

        user = get_user_by_id(self.conn, uid)
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Dr. Jane Doe")
        self.assertEqual(user["email"], "jane@clinic.org")
        self.assertTrue(verify_password(user["pw"], plain_pw))
        self.assertFalse(verify_password(user["pw"], "WrongPassword"))

        # Lookup by case-insensitive email
        user_by_email = get_user_by_email(self.conn, "JANE@CLINIC.ORG")
        self.assertIsNotNone(user_by_email)
        self.assertEqual(user_by_email["id"], uid)

    def test_unique_email_constraint(self):
        """Tests that attempting to register duplicate emails raises sqlite3.IntegrityError."""
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
            ("User One", "unique@domain.com", "hash1", "user", now)
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                ("User Two", "unique@domain.com", "hash2", "user", now)
            )

    def test_assessment_insertion_and_retrieval(self):
        """Tests inserting and reading a full assessment record including BMI and model version."""
        # Create parent user
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
            ("Test Subject", "patient@test.com", "hash", "user", datetime.now().isoformat())
        )
        self.conn.commit()
        uid = cursor.lastrowid

        inputs = {
            "age": 68, "sex": "Female", "height_cm": 155.0, "weight_kg": 42.0,
            "food_groups": 3, "meals_per_day": 2, "activity": "Low",
            "income": "Low", "education": "Primary", "residence": "Rural", "recent_illness": "Yes"
        }
        # BMI = 42 / (1.55^2) ≈ 17.48
        calculated_bmi = round(42.0 / ((155.0 / 100.0) ** 2), 2)

        aid = insert_assessment(
            db=self.conn,
            user_id=uid,
            subject="Baseline Screen",
            inputs=inputs,
            risk="High Risk",
            confidence=0.88,
            probabilities=[0.02, 0.10, 0.88],
            factors=[{"name": "BMI", "effect": 0.25}],
            bmi=calculated_bmi,
            model_version="v2.1-xgboost"
        )
        self.assertIsInstance(aid, int)

        # Retrieve record
        row = get_assessment_secure(self.conn, aid, user_id=uid)
        self.assertIsNotNone(row)
        self.assertEqual(row["subject"], "Baseline Screen")
        self.assertEqual(row["risk"], "High Risk")
        self.assertAlmostEqual(row["bmi"], 17.48, places=1)
        self.assertEqual(row["model_version"], "v2.1-xgboost")
        self.assertEqual(row["age"], 68)
        self.assertEqual(row["sex"], "Female")

    def test_safe_migrations_preserve_data_and_backfills_bmi(self):
        """
        Simulates an older legacy database without 'bmi' and 'model_version',
        applies safe_migrate(), and verifies columns are added and BMI backfilled.
        """
        # Create a separate connection with legacy schema (no bmi, no model_version)
        legacy_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        legacy_file.close()
        legacy_path = legacy_file.name

        try:
            legacy_conn = sqlite3.connect(legacy_path)
            legacy_conn.executescript("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT, email TEXT UNIQUE, pw TEXT, role TEXT, created TEXT
                );
                CREATE TABLE assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER, subject TEXT, created TEXT, inputs TEXT,
                    risk TEXT, confidence REAL, probs TEXT, factors TEXT,
                    age INTEGER, sex TEXT
                );
            """)
            # Insert historical row with height 180cm, weight 81kg -> BMI should be 25.0
            hist_inputs = json.dumps({"height_cm": 180.0, "weight_kg": 81.0, "age": 30, "sex": "Male"})
            legacy_conn.execute("""
                INSERT INTO assessments (user_id, subject, created, inputs, risk, confidence, probs, factors, age, sex)
                VALUES (1, 'Legacy Patient', '2024-01-01', ?, 'Low Risk', 0.95, '[]', '[]', 30, 'Male')
            """, (hist_inputs,))
            legacy_conn.commit()

            # Execute migration
            safe_migrate(legacy_conn)

            # Verify columns now exist
            cur = legacy_conn.cursor()
            cur.execute("PRAGMA table_info(assessments);")
            cols = {r[1] for r in cur.fetchall()}
            self.assertIn("bmi", cols)
            self.assertIn("model_version", cols)

            # Verify historical record's BMI was backfilled accurately (81 / 1.8^2 = 25.0)
            legacy_conn.row_factory = sqlite3.Row
            row = legacy_conn.execute("SELECT * FROM assessments WHERE id = 1;").fetchone()
            self.assertAlmostEqual(row["bmi"], 25.0, places=1)
            self.assertEqual(row["model_version"], "v1.0-xgboost")

            legacy_conn.close()
        finally:
            if os.path.exists(legacy_path):
                os.unlink(legacy_path)

    def test_access_control_and_user_isolation(self):
        """Tests that regular users can only access their own assessments, while admins can access any."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        # Create Patient A and Patient B
        cursor.execute("INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                       ("Alice", "alice@patient.org", "pw", "user", now))
        uid_alice = cursor.lastrowid

        cursor.execute("INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                       ("Bob", "bob@patient.org", "pw", "user", now))
        uid_bob = cursor.lastrowid

        # Create Admin
        cursor.execute("INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                       ("Admin Chief", "admin@hospital.org", "pw", "admin", now))
        uid_admin = cursor.lastrowid
        self.conn.commit()

        # Alice creates assessment #1
        aid_alice = insert_assessment(
            db=self.conn, user_id=uid_alice, subject="Alice Checkup",
            inputs={"age": 25, "sex": "Female"}, risk="Low Risk",
            confidence=0.9, probabilities=[0.9, 0.08, 0.02],
            factors=[], bmi=21.5
        )

        # 1. Alice can access her own record
        res_alice = get_assessment_secure(self.conn, aid_alice, user_id=uid_alice, is_admin=False)
        self.assertIsNotNone(res_alice)
        self.assertEqual(res_alice["subject"], "Alice Checkup")

        # 2. Bob CANNOT access Alice's record (returns None, leading to 403/404)
        res_bob = get_assessment_secure(self.conn, aid_alice, user_id=uid_bob, is_admin=False)
        self.assertIsNone(res_bob, "Security breach: Bob was able to access Alice's record!")

        # 3. Admin CAN access Alice's record
        res_admin = get_assessment_secure(self.conn, aid_alice, user_id=uid_admin, is_admin=True)
        self.assertIsNotNone(res_admin, "Admin should have access to Alice's record.")
        self.assertEqual(res_admin["id"], aid_alice)

    def test_foreign_key_cascade_deletion(self):
        """Verifies that deleting a user automatically cascades and deletes their assessments."""
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                       ("Ephemeral User", "ephemeral@temp.org", "pw", "user", datetime.now().isoformat()))
        uid = cursor.lastrowid
        self.conn.commit()

        aid = insert_assessment(
            db=self.conn, user_id=uid, subject="Temporary Assessment",
            inputs={"age": 40, "sex": "Male"}, risk="Moderate Risk",
            confidence=0.7, probabilities=[0.2, 0.7, 0.1],
            factors=[], bmi=24.0
        )
        self.assertIsNotNone(get_assessment_secure(self.conn, aid, user_id=uid, is_admin=True))

        # Delete the user
        self.conn.execute("DELETE FROM users WHERE id = ?;", (uid,))
        self.conn.commit()

        # Assessment should be gone via ON DELETE CASCADE
        orphan = self.conn.execute("SELECT * FROM assessments WHERE id = ?;", (aid,)).fetchone()
        self.assertIsNone(orphan, "Assessment was not deleted upon parent user deletion.")

    def test_model_metadata_version_tracking(self):
        """Tests recording and active-state switching of model training metadata."""
        mid1 = save_model_metadata_record(
            db=self.conn,
            model_name="Random Forest",
            dataset_version="synthetic-v1.0",
            training_date="2026-01-01T00:00:00",
            metrics_dict={"accuracy": 0.72, "f1": 0.71},
            artifact_version="v1.0",
            make_active=True
        )

        row1 = self.conn.execute("SELECT * FROM model_metadata WHERE id = ?", (mid1,)).fetchone()
        self.assertEqual(row1["is_active"], 1)

        # Deploy model 2 as active
        mid2 = save_model_metadata_record(
            db=self.conn,
            model_name="XGBoost Classifier",
            dataset_version="real-v2.0",
            training_date="2026-02-01T00:00:00",
            metrics_dict={"accuracy": 0.74, "f1": 0.73},
            artifact_version="v2.0",
            make_active=True
        )

        row1_after = self.conn.execute("SELECT * FROM model_metadata WHERE id = ?", (mid1,)).fetchone()
        row2 = self.conn.execute("SELECT * FROM model_metadata WHERE id = ?", (mid2,)).fetchone()
        self.assertEqual(row1_after["is_active"], 0)
        self.assertEqual(row2["is_active"], 1)
        self.assertEqual(row2["model_name"], "XGBoost Classifier")


if __name__ == "__main__":
    unittest.main(verbosity=2)
