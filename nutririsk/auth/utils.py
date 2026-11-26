from functools import wraps
from flask import session, redirect, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password: str) -> str:
    """Hashes a plaintext password using Werkzeug's secure Scrypt hash with a 16-byte random salt."""
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")
    return generate_password_hash(password, method="scrypt", salt_length=16)

def verify_password(hashed_pw: str, password: str) -> bool:
    """Verifies a plaintext password against the stored hash in constant time."""
    if not hashed_pw or not password:
        return False
    try:
        return check_password_hash(hashed_pw, password)
    except Exception:
        return False

def login_required(f):
    """Decorator ensuring that a route can only be accessed by authenticated users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "uid" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator ensuring that a route can only be accessed by users with admin privileges."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
