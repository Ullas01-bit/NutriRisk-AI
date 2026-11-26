"""
Database management module for NutriRisk AI.

Provides SQLite initialization, safe automated migrations, connection pooling,
parameterized query helpers, and access control enforcement.

Tables Supported:
  1. users: User authentication and role-based access control.
  2. assessments: Nutritional risk screening history and model outputs.
  3. model_metadata: ML model versioning, training dates, and evaluation metrics.
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from flask import g, current_app

logger = logging.getLogger(__name__)


def get_db() -> sqlite3.Connection:
    """
    Returns the active SQLite database connection for the current Flask request context.
    Configures row_factory to sqlite3.Row for dictionary-like column access
    and enforces foreign key constraints.
    """
    if "db" not in g:
        db_path = current_app.config.get("DATABASE_PATH", "nutririsk.db")
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e: Optional[BaseException] = None) -> None:
    """Closes the database connection upon request teardown."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def safe_migrate(conn: sqlite3.Connection) -> None:
    """
    Applies non-destructive schema migrations to preserve existing user and assessment data.
    Checks existing table columns and safely adds missing columns (e.g. bmi, model_version).
    Backfills missing BMI values for historical records from their inputs JSON.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(assessments);")
    existing_cols = {row[1] for row in cursor.fetchall()}

    # 1. Add 'bmi' column if absent
    if "bmi" not in existing_cols:
        logger.info("Migrating schema: Adding column 'bmi' to assessments table.")
        cursor.execute("ALTER TABLE assessments ADD COLUMN bmi REAL DEFAULT 0.0;")
        conn.commit()

    # 2. Add 'model_version' column if absent
    if "model_version" not in existing_cols:
        logger.info("Migrating schema: Adding column 'model_version' to assessments table.")
        cursor.execute("ALTER TABLE assessments ADD COLUMN model_version TEXT DEFAULT 'v1.0-xgboost';")
        conn.commit()

    # 3. Ensure admin_audit_logs table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            admin_name TEXT NOT NULL,
            action TEXT NOT NULL,
            target_user_id INTEGER,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()

    # 4. Add 'face_enrolled' and 'face_descriptor' to users table if absent
    cursor.execute("PRAGMA table_info(users);")
    user_cols = {row[1] for row in cursor.fetchall()}
    if "face_enrolled" not in user_cols:
        logger.info("Migrating schema: Adding column 'face_enrolled' to users table.")
        cursor.execute("ALTER TABLE users ADD COLUMN face_enrolled INTEGER DEFAULT 0;")
        conn.commit()
    if "face_descriptor" not in user_cols:
        logger.info("Migrating schema: Adding column 'face_descriptor' to users table.")
        cursor.execute("ALTER TABLE users ADD COLUMN face_descriptor TEXT DEFAULT '';")
        conn.commit()

    # 5. Backfill BMI for any existing rows where bmi == 0.0
    cursor.execute("SELECT id, inputs FROM assessments WHERE bmi = 0.0 OR bmi IS NULL;")
    rows_to_backfill = cursor.fetchall()
    for aid, inputs_raw in rows_to_backfill:
        try:
            inp = json.loads(inputs_raw)
            h_m = float(inp.get("height_cm", 170.0)) / 100.0
            w_kg = float(inp.get("weight_kg", 70.0))
            computed_bmi = round(w_kg / (h_m ** 2), 2)
            cursor.execute("UPDATE assessments SET bmi = ? WHERE id = ?", (computed_bmi, aid))
        except Exception as err:
            logger.warning("Could not backfill BMI for assessment #%d: %s", aid, err)
    if rows_to_backfill:
        conn.commit()
        logger.info("Backfilled BMI for %d historical assessment records.", len(rows_to_backfill))

    # 6. Ensure otp_verifications table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'login',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_otp_email_purpose ON otp_verifications(email, purpose);")
    conn.commit()


def init_db(app) -> None:
    """
    Initializes database tables, constraints, indexes, and applies safe migrations.
    """
    db_path = app.config.get("DATABASE_PATH", "nutririsk.db")
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. Core Schema Creation
    cursor.executescript("""
        -- Users Table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            pw TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created TEXT NOT NULL,
            face_enrolled INTEGER NOT NULL DEFAULT 0,
            face_descriptor TEXT DEFAULT ''
        );

        -- Assessments Table
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            created TEXT NOT NULL,
            inputs TEXT NOT NULL,
            risk TEXT NOT NULL,
            confidence REAL NOT NULL,
            probs TEXT NOT NULL,
            factors TEXT NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            bmi REAL NOT NULL DEFAULT 0.0,
            model_version TEXT NOT NULL DEFAULT 'v1.0-xgboost',
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        -- ML Model Metadata & Audit Table
        CREATE TABLE IF NOT EXISTS model_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            dataset_version TEXT NOT NULL,
            training_date TEXT NOT NULL,
            metrics TEXT NOT NULL,
            artifact_version TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        -- Administrative Action Audit Log Table
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            admin_name TEXT NOT NULL,
            action TEXT NOT NULL,
            target_user_id INTEGER,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- One-Time Password (OTP) Verification Table
        CREATE TABLE IF NOT EXISTS otp_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'login',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );

        -- Indexes for High-Performance Queries
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_assessments_user_id ON assessments(user_id);
        CREATE INDEX IF NOT EXISTS idx_assessments_risk ON assessments(risk);
        CREATE INDEX IF NOT EXISTS idx_assessments_created ON assessments(created);
        CREATE INDEX IF NOT EXISTS idx_model_metadata_active ON model_metadata(is_active);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON admin_audit_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_otp_email_purpose ON otp_verifications(email, purpose);
    """)
    conn.commit()

    # 2. Apply non-destructive migrations to older database instances
    safe_migrate(conn)

    # 3. Seed active model metadata if table is currently empty
    cursor.execute("SELECT COUNT(*) FROM model_metadata;")
    if cursor.fetchone()[0] == 0:
        metrics_file = app.config.get("METRICS_PATH", "model/metrics.json")
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    metrics_json = json.load(f)
                best_name = metrics_json.get("best", "XGBoost")
                src_label = metrics_json.get("data_source_label", "SYNTHETIC")
                now_str = datetime.now().isoformat(timespec="seconds")
                cursor.execute("""
                    INSERT INTO model_metadata 
                    (model_name, dataset_version, training_date, metrics, artifact_version, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (
                    f"{best_name} Classifier",
                    f"{src_label.lower()}-v1.0",
                    now_str,
                    json.dumps(metrics_json.get("models", {}).get(best_name, {})),
                    "v1.0-joblib",
                    now_str
                ))
                conn.commit()
                logger.info("Seeded initial active model metadata into database.")
            except Exception as e:
                logger.warning("Could not seed model metadata from '%s': %s", metrics_file, e)

    conn.close()
    logger.info("Database initialized successfully at: %s", db_path)


# ─────────────────────────────────────────────────────────────────────────────
# Parameterized Query & Access Control Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_user_by_id(db: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    """Retrieves a single user record by primary key."""
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(db: sqlite3.Connection, email: str) -> Optional[sqlite3.Row]:
    """Retrieves a single user record by unique email address (case-insensitive)."""
    return db.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),)).fetchone()


def get_assessment_secure(
    db: sqlite3.Connection,
    assessment_id: int,
    user_id: int,
    is_admin: bool = False
) -> Optional[sqlite3.Row]:
    """
    Secure assessment retrieval with strict multi-tenant access control.
    - Administrators can view any assessment.
    - Regular users can ONLY access assessments where user_id matches their session.
    """
    if is_admin:
        return db.execute("SELECT * FROM assessments WHERE id = ?", (assessment_id,)).fetchone()
    return db.execute(
        "SELECT * FROM assessments WHERE id = ? AND user_id = ?",
        (assessment_id, user_id)
    ).fetchone()


def insert_assessment(
    db: sqlite3.Connection,
    user_id: int,
    subject: str,
    inputs: Dict[str, Any],
    risk: str,
    confidence: float,
    probabilities: List[float],
    factors: List[Dict[str, Any]],
    bmi: float,
    model_version: str = "v1.0-xgboost"
) -> int:
    """
    Inserts a newly completed risk assessment using strictly parameterized queries.
    Returns the integer primary key ID of the inserted record.
    """
    created_at = datetime.now().isoformat(timespec="seconds")
    cursor = db.execute(
        """INSERT INTO assessments 
           (user_id, subject, created, inputs, risk, confidence, probs, factors, age, sex, bmi, model_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            subject.strip() or "Self Assessment",
            created_at,
            json.dumps(inputs),
            risk,
            confidence,
            json.dumps(probabilities),
            json.dumps(factors),
            int(inputs.get("age", 0)),
            str(inputs.get("sex", "")),
            float(bmi),
            model_version
        )
    )
    db.commit()
    return cursor.lastrowid


def save_model_metadata_record(
    db: sqlite3.Connection,
    model_name: str,
    dataset_version: str,
    training_date: str,
    metrics_dict: Dict[str, Any],
    artifact_version: str = "v1.0-joblib",
    make_active: bool = True
) -> int:
    """
    Records new model training metadata in SQLite and updates active flags.
    """
    now_str = datetime.now().isoformat(timespec="seconds")
    if make_active:
        db.execute("UPDATE model_metadata SET is_active = 0;")
    cursor = db.execute(
        """INSERT INTO model_metadata 
           (model_name, dataset_version, training_date, metrics, artifact_version, is_active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            model_name,
            dataset_version,
            training_date,
            json.dumps(metrics_dict),
            artifact_version,
            1 if make_active else 0,
            now_str
        )
    )
    db.commit()
    return cursor.lastrowid


def get_active_model_metadata(db: sqlite3.Connection) -> Optional[sqlite3.Row]:
    """Retrieves the active model metadata record from SQLite."""
    cursor = db.execute(
        "SELECT * FROM model_metadata WHERE is_active = 1 ORDER BY id DESC LIMIT 1;"
    )
    return cursor.fetchone()


def log_admin_action(
    db: sqlite3.Connection,
    admin_id: int,
    admin_name: str,
    action: str,
    target_user_id: Optional[int],
    details: str
) -> int:
    """Records an administrative event to the audit trail table."""
    now_str = datetime.now().isoformat(timespec="seconds")
    cursor = db.execute(
        """INSERT INTO admin_audit_logs 
           (admin_id, admin_name, action, target_user_id, details, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (admin_id, admin_name, action, target_user_id, details, now_str)
    )
    db.commit()
    return cursor.lastrowid


def create_otp(
    db: sqlite3.Connection,
    email: str,
    purpose: str = "login",
    validity_seconds: int = 600
) -> str:
    """
    Generates a secure 6-digit OTP code, stores it in otp_verifications with an expiration timestamp.
    Invalidates any previous unused OTPs for the same email and purpose.
    """
    import secrets
    from datetime import datetime, timedelta

    clean_email = email.strip().lower()

    # Invalidate previous unused OTPs for this email and purpose
    db.execute(
        "UPDATE otp_verifications SET used = 1 WHERE email = ? AND purpose = ? AND used = 0",
        (clean_email, purpose)
    )

    # Cryptographically secure 6-digit random code (100000 - 999999)
    otp = f"{secrets.randbelow(900000) + 100000}"

    from datetime import timezone
    now = datetime.now(timezone.utc)
    created_at = now.isoformat(timespec="seconds")
    expires_at = (now + timedelta(seconds=validity_seconds)).isoformat(timespec="seconds")

    db.execute(
        """INSERT INTO otp_verifications (email, otp, purpose, created_at, expires_at, used)
           VALUES (?, ?, ?, ?, ?, 0)""",
        (clean_email, otp, purpose, created_at, expires_at)
    )
    db.commit()
    logger.info("Generated %s OTP for email: %s (expires: %s)", purpose, clean_email, expires_at)
    return otp


def verify_otp(
    db: sqlite3.Connection,
    email: str,
    otp: str,
    purpose: str = "login"
) -> Tuple[bool, str]:
    """
    Validates a submitted OTP for a given email and purpose.
    Checks: matching code, not already used, not expired.
    Marks OTP as used upon successful verification.
    Returns: (is_valid: bool, message: str)
    """
    from datetime import datetime

    clean_email = email.strip().lower()
    clean_otp = str(otp).strip()

    if not clean_otp or len(clean_otp) != 6:
        return False, "Please enter a valid 6-digit verification code."

    cursor = db.execute(
        """SELECT id, otp, expires_at, used FROM otp_verifications
           WHERE email = ? AND purpose = ? AND used = 0
           ORDER BY id DESC LIMIT 1""",
        (clean_email, purpose)
    )
    record = cursor.fetchone()

    if not record:
        return False, "No active verification code found for this email. Please request a new OTP."

    if record["otp"] != clean_otp:
        return False, "Incorrect verification code. Please check and re-enter."

    # Expiration check
    try:
        from datetime import timezone
        expires_at = datetime.fromisoformat(record["expires_at"])
        now_cmp = datetime.now(timezone.utc) if expires_at.tzinfo is not None else datetime.now()
        if now_cmp > expires_at:
            return False, "Verification code has expired. Please request a fresh OTP."
    except Exception as e:
        logger.warning("Error evaluating OTP expiry: %s", e)
        return False, "Verification code has expired. Please request a fresh OTP."

    # Mark as used
    db.execute("UPDATE otp_verifications SET used = 1 WHERE id = ?", (record["id"],))
    db.commit()
    logger.info("Successfully verified %s OTP for email: %s", purpose, clean_email)
    return True, "Verification successful."



