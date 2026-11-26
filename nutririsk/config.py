"""
Application Configuration for NutriRisk AI (Prompt 21).

Implements environment-based secret configuration, secure session handling,
cookie security flags, safe artifact path declarations, and clinical constants.
"""
import os
import secrets
import logging
from datetime import timedelta
from pathlib import Path

logger = logging.getLogger("nutririsk.config")

# Base directory of the repository root
BASE_PATH = Path(__file__).resolve().parent.parent

# Attempt to load environment variables from local .env if present
env_file = BASE_PATH / ".env"
if env_file.exists():
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        logger.warning("Could not read local .env file: %s", e)


def _get_secret_key() -> str:
    """
    Retrieves the application SECRET_KEY from environment variables.
    In development without a specified key, issues a security audit warning.
    """
    key = os.environ.get("SECRET_KEY")
    if not key:
        # Fallback for academic development / test environments
        key = "nutririsk-academic-prototype-key-2026"
        if os.environ.get("FLASK_ENV") == "production":
            logger.critical(
                "SECURITY WARNING: Running in production without a custom SECRET_KEY! "
                "Set the SECRET_KEY environment variable immediately."
            )
    return key


class Config:
    """Production-grade application configuration settings."""

    # Base repository root
    BASE_DIR = str(BASE_PATH)

    # Secret key for cryptographic signing of session cookies
    SECRET_KEY = _get_secret_key()

    # Flask Execution Environment
    ENV = os.environ.get("FLASK_ENV", "production")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    TESTING = False

    # CSRF Protection Setting
    WTF_CSRF_ENABLED = os.environ.get("CSRF_ENABLED", "1") == "1"

    # Evaluation / Demonstration Mode (Enables on-screen demo OTP tokens for academic viva/testing)
    # Automatically disabled in production unless explicitly opted in via DEMO_MODE=1
    DEMO_MODE = os.environ.get("DEMO_MODE", "1" if (DEBUG or TESTING or ENV != "production") else "0") == "1"

    # Database Configuration
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_PATH / "nutririsk.db"))

    # ML Model & Artifacts
    MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_PATH / "model" / "model.joblib"))
    METRICS_PATH = os.environ.get("METRICS_PATH", str(BASE_PATH / "model" / "metrics.json"))

    # Data Paths
    DATA_PATH = os.environ.get("DATA_PATH", str(BASE_PATH / "data" / "dataset.csv"))
    SYNTHETIC_DATA_PATH = os.environ.get("SYNTHETIC_DATA_PATH", str(BASE_PATH / "data" / "synthetic_dataset.csv"))

    # ─────────────────────────────────────────────────────────────────────────
    # Secure Session & Cookie Flags (Prompt 21 Item 5)
    # ─────────────────────────────────────────────────────────────────────────
    # Prevents client-side scripts from reading the session cookie (XSS mitigation)
    SESSION_COOKIE_HTTPONLY = True

    # Mitigates cross-site request forgery via strict/lax cookie delivery
    SESSION_COOKIE_SAMESITE = "Lax"

    # Encrypted cookie transmission; enabled in HTTPS environments
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # Session lifetime: 8 hours of clinical screening activity
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # ─────────────────────────────────────────────────────────────────────────
    # Clinical Stratification Protocol Directives
    # ─────────────────────────────────────────────────────────────────────────
    ADVICE = {
        "Low Risk": (
            "Nutritional parameters are within standard baseline ranges. Continue maintaining a balanced, "
            "varied diet, regular physical activity, and routine periodic check-ups."
        ),
        "Moderate Risk": (
            "Sub-optimal nutritional or lifestyle indicators detected. Recommended actions include increasing "
            "dietary diversity, optimizing meal frequency, and scheduling a routine nutritional review."
        ),
        "High Risk": (
            "Elevated probability of nutritional vulnerability or malnutrition. Prompt comprehensive assessment "
            "by a qualified healthcare professional or clinical dietitian is advised."
        )
    }

    # Institutional Academic Decision Support Disclaimer
    DISCLAIMER = (
        "NutriRisk AI is an academic clinical decision-support research prototype developed "
        "for screening and risk stratification. It does not provide medical diagnoses or replace "
        "professional clinical evaluations."
    )
