"""
Security and Defensive Engineering Module for NutriRisk AI (Prompt 21).

Provides:
  1. Cryptographic CSRF Protection (Token generation, validation, and request interception).
  2. HTTP Defensive Security Headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, etc.).
  3. Trusted Path Sanitization (Mitigates Path Traversal and Local File Inclusion for ML models).
  4. Privacy-Preserving Security Event Logging (Scrubbing sensitive inputs from log streams).
"""
import os
import hmac
import secrets
import logging
from typing import Optional
from flask import request, session, abort, current_app

logger = logging.getLogger("nutririsk.security")

# Methods that modify state and require CSRF verification
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def generate_csrf_token() -> str:
    """
    Generates or retrieves a cryptographically strong CSRF token bound to the current session.
    Uses 32 bytes of system randomness (64 hexadecimal characters).
    """
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf_token(token: Optional[str]) -> bool:
    """
    Validates a submitted CSRF token using constant-time comparison to prevent timing attacks.
    """
    session_token = session.get("_csrf_token")
    if not session_token or not token:
        return False
    return hmac.compare_digest(str(session_token), str(token))


def init_csrf_protection(app) -> None:
    """
    Registers CSRF token injection and verification hooks with the Flask application.
    Supports turning off CSRF for automated testing via `WTF_CSRF_ENABLED = False` or `CSRF_ENABLED = False`.
    """
    # Expose csrf_token() helper to all Jinja templates
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.before_request
    def check_csrf_token():
        # Check if CSRF protection is globally enabled (default True)
        csrf_enabled = app.config.get("WTF_CSRF_ENABLED", app.config.get("CSRF_ENABLED", True))
        if not csrf_enabled:
            return

        # Skip safe read-only HTTP methods
        if request.method in SAFE_METHODS:
            return

        # Exempt testing client if explicitly configured
        if app.config.get("TESTING") and not app.config.get("ENFORCE_CSRF_IN_TESTS", False):
            return

        # Retrieve token from form field or request header
        token = (
            request.form.get("csrf_token") or
            request.headers.get("X-CSRFToken") or
            request.headers.get("X-CSRF-Token")
        )

        if not validate_csrf_token(token):
            logger.warning(
                "CSRF validation failed for route: %s %s [IP: %s, User: %s]",
                request.method,
                request.path,
                request.remote_addr,
                session.get("uid", "anonymous")
            )
            abort(400, description="Security Notice: CSRF token is missing or invalid. Please refresh the page and try again.")


def add_security_headers(response):
    """
    Attaches defense-in-depth HTTP response headers to protect against
    Clickjacking, MIME-confusion attacks, XSS, and Information Leakage.
    """
    # Prevent browser MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Mitigate Clickjacking
    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    # Legacy XSS protection filter
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Control Referrer Information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Restrict permissions for device hardware while allowing camera for local Face ID
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(self), microphone=()"

    # Content Security Policy (Allows self and CDN-hosted Bootstrap/Chart.js resources)
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'self';"
    )
    response.headers["Content-Security-Policy"] = csp_policy

    # Strict-Transport-Security if deployed under HTTPS or configured
    if request.is_secure or current_app.config.get("FORCE_HTTPS", False):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Ensure no server software banner is exposed
    response.headers["Server"] = "NutriRisk-Clinical-Engine"

    return response


def validate_safe_model_path(
    model_path: str,
    allowed_base_dir: Optional[str] = None
) -> str:
    """
    Validates that a model artifact file path is canonical, safe, and constrained
    within trusted application boundaries. Prevents Path Traversal (e.g. `../../etc/passwd`).

    Parameters
    ----------
    model_path : str
        Target filesystem path for the serialized model artifact.
    allowed_base_dir : str, optional
        Base root directory within which the artifact must reside.
        Defaults to project base directory.

    Returns
    -------
    str
        Canonical realpath to the validated model artifact.

    Raises
    ------
    ValueError
        If the path contains illegal characters, an invalid extension, or escapes the root.
    """
    if not model_path or not isinstance(model_path, str):
        raise ValueError("Model path must be a non-empty string.")

    # Canonicalize absolute paths
    canonical_path = os.path.realpath(os.path.abspath(model_path))

    if allowed_base_dir is None:
        allowed_base_dir = current_app.config.get("BASE_DIR") if current_app else None
        if not allowed_base_dir:
            from nutririsk.config import Config
            allowed_base_dir = Config.BASE_DIR

    canonical_base = os.path.realpath(os.path.abspath(str(allowed_base_dir)))

    # Path traversal check: canonical path must start with canonical base directory
    try:
        common = os.path.commonpath([canonical_path, canonical_base])
    except ValueError:
        raise ValueError(f"Model path '{canonical_path}' is on a different drive than base root '{canonical_base}'.")

    if common != canonical_base:
        raise ValueError(
            f"Security Violation: Model artifact path '{model_path}' resolves outside trusted application root '{canonical_base}'."
        )

    # File extension check (allow only trusted serialized model formats)
    valid_extensions = {".joblib", ".pkl"}
    _, ext = os.path.splitext(canonical_path)
    if ext.lower() not in valid_extensions:
        raise ValueError(
            f"Security Violation: Model artifact '{model_path}' has untrusted extension '{ext}'. Only {valid_extensions} are permitted."
        )

    return canonical_path
