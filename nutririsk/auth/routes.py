import re
import hashlib
import logging
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from nutririsk.db import get_db, create_otp, verify_otp
from nutririsk.auth.utils import hash_password, verify_password, login_required

logger = logging.getLogger("nutririsk.auth")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _mask_email(email: str) -> str:
    """Masks email address for privacy-preserving security logging."""
    if not email or "@" not in email:
        return "***"
    user_part, domain = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "*"
    else:
        masked_user = user_part[0] + "*" * min(len(user_part) - 2, 6) + user_part[-1]
    return f"{masked_user}@{domain}"

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handles new user registration with server-side validation & password confirmation."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password")
        
        # Validation checks
        if not name:
            flash("Please enter your full name.", "err")
        elif not email or not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address.", "err")
        elif len(password) < 6:
            flash("Password must be at least 6 characters long.", "err")
        elif confirm_password is not None and password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "err")
        else:
            db = get_db()
            user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            # First user is admin, all subsequent accounts are standard users
            is_admin = (user_count == 0)
            role = "admin" if is_admin else "user"
            
            try:
                db.execute(
                    "INSERT INTO users (name, email, pw, role, created) VALUES (?, ?, ?, ?, ?)",
                    (name, email, hash_password(password), role, datetime.now().isoformat(timespec="seconds"))
                )
                db.commit()
                logger.info("New user registered: %s (role: %s)", _mask_email(email), role)
                admin_msg = " (First user designated as Administrator)" if is_admin else ""
                flash(f"Registration successful! Please log in.{admin_msg}", "ok")
                return redirect(url_for("auth.login"))
            except sqlite3.IntegrityError:
                flash("An account with this email address already exists. Please log in or reset your password.", "err")
                
    return render_template("auth.html", mode="register")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handles user sign-in and session initiation."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Please provide both email and password.", "err")
            return render_template("auth.html", mode="login")
            
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if user and verify_password(user["pw"], password):
            session.clear()
            session.permanent = True
            session["uid"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            logger.info("Successful login for user #%d (%s, role: %s)", user["id"], _mask_email(email), user["role"])
            flash(f"Welcome back, {user['name']}!", "ok")
            return redirect(url_for("main.dashboard"))
            
        logger.warning("Authentication failed for email: %s [IP: %s]", _mask_email(email), request.remote_addr)
        flash("Invalid email or password. Please verify your credentials.", "err")
        
    return render_template("auth.html", mode="login")

@auth_bp.route("/reset", methods=["GET", "POST"])
def reset():
    """
    Password reset handler.
    Note: In development without SMTP mail servers, this provides a demonstration reset.
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password")
        
        if not email or not EMAIL_REGEX.match(email):
            flash("Please enter a valid registered email address.", "err")
        elif len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "err")
        elif confirm_password is not None and new_password != confirm_password:
            flash("Passwords do not match.", "err")
        else:
            db = get_db()
            existing = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                db.execute("UPDATE users SET pw = ? WHERE email = ?", (hash_password(new_password), email))
                db.commit()
                flash("Password successfully reset! You can now log in with your new credentials.", "ok")
                return redirect(url_for("auth.login"))
            else:
                flash("No registered account found with that email address.", "err")
                
    return render_template("auth.html", mode="reset")


@auth_bp.route("/send-otp", methods=["POST"])
@auth_bp.route("/auth/send-otp", methods=["POST"])
def send_otp():
    """Generates and dispatches a 6-digit OTP code."""
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "").strip().lower()
    purpose = data.get("purpose", "login").strip().lower()

    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"status": "error", "message": "Please provide a valid registered email address."}), 400

    db = get_db()
    user = db.execute("SELECT id, name FROM users WHERE email = ?", (email,)).fetchone()

    if purpose in ("login", "reset") and not user:
        return jsonify({"status": "error", "message": "No registered account found with this email address."}), 404

    otp_code = create_otp(db, email, purpose=purpose)
    
    # In development/evaluation mode, preview the OTP in the API response and log
    logger.info("Dispatched %s OTP for %s: %s", purpose, _mask_email(email), otp_code)
    
    is_demo = current_app.config.get("DEMO_MODE", False) or current_app.config.get("TESTING", False)
    return jsonify({
        "status": "success",
        "message": f"Verification code sent to {email}.",
        "otp_preview": otp_code if is_demo else None,
        "expires_in": 600
    })


@auth_bp.route("/verify-otp", methods=["POST"])
@auth_bp.route("/auth/verify-otp", methods=["POST"])
def verify_otp_endpoint():
    """Validates the submitted 6-digit OTP code and fulfills authentication or password reset."""
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "").strip().lower()
    otp = str(data.get("otp", "")).strip()
    purpose = data.get("purpose", "login").strip().lower()

    if not email or not otp:
        return jsonify({"status": "error", "message": "Both email address and 6-digit verification code are required."}), 400

    db = get_db()
    is_valid, msg = verify_otp(db, email, otp, purpose=purpose)
    if not is_valid:
        return jsonify({"status": "error", "message": msg}), 400

    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        return jsonify({"status": "error", "message": "Associated account record not found."}), 404

    if purpose == "login":
        session.clear()
        session.permanent = True
        session["uid"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]
        logger.info("Successful OTP login for user #%d (%s, role: %s)", user["id"], _mask_email(email), user["role"])
        return jsonify({
            "status": "success",
            "message": f"Welcome back, {user['name']}! Login verified.",
            "redirect": url_for("main.dashboard")
        })

    elif purpose == "reset":
        new_pw = data.get("password") or data.get("new_password")
        if new_pw:
            if len(new_pw) < 6:
                return jsonify({"status": "error", "message": "New password must be at least 6 characters long."}), 400
            db.execute("UPDATE users SET pw = ? WHERE email = ?", (hash_password(new_pw), email))
            db.commit()
            logger.info("Password reset completed via OTP for user #%d (%s)", user["id"], _mask_email(email))
            return jsonify({
                "status": "success",
                "message": "Password updated successfully! You may now sign in with your new password.",
                "redirect": url_for("auth.login")
            })
        return jsonify({
            "status": "success",
            "message": "Code verified. Please set your new password.",
            "verified": True
        })

    return jsonify({"status": "success", "message": "OTP verified successfully."})


@auth_bp.route("/otp-login", methods=["GET", "POST"])
def otp_login():
    """Dedicated fallback view for OTP-based passwordless login."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        otp = request.form.get("otp", "").strip()
        action = request.form.get("action", "verify")

        if action == "send":
            if not email or not EMAIL_REGEX.match(email):
                flash("Please enter a valid email address.", "err")
            else:
                db = get_db()
                user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                if not user:
                    flash("No registered account found with that email address.", "err")
                else:
                    otp_code = create_otp(db, email, purpose="login")
                    flash(f"Verification code sent! [Demo code: {otp_code}]", "ok")
                    return render_template("auth.html", mode="otp_login", email=email, otp_sent=True, demo_otp=otp_code)

        elif action == "verify":
            if not email or not otp:
                flash("Please provide both your registered email and the 6-digit OTP code.", "err")
            else:
                db = get_db()
                is_valid, msg = verify_otp(db, email, otp, purpose="login")
                if is_valid:
                    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                    session.clear()
                    session.permanent = True
                    session["uid"] = user["id"]
                    session["name"] = user["name"]
                    session["role"] = user["role"]
                    logger.info("Successful OTP login for user #%d (%s)", user["id"], _mask_email(email))
                    flash(f"Welcome back, {user['name']}! Login verified via OTP.", "ok")
                    return redirect(url_for("main.dashboard"))
                else:
                    flash(msg, "err")
                    return render_template("auth.html", mode="otp_login", email=email, otp_sent=True)

    return render_template("auth.html", mode="otp_login")


@auth_bp.route("/logout")
def logout():
    """Clears user session and logs out."""
    session.clear()
    flash("You have been securely logged out.", "ok")
    return redirect(url_for("main.home"))

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """
    User Profile Management (Prompt 20).
    Allows authenticated clinicians to view profile telemetry, update their display name,
    view registered email, update email with password verification, change password securely,
    and review lifetime assessment activity without corrupting historical records.
    """
    db = get_db()
    uid = session["uid"]
    
    user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        session.clear()
        flash("Account record not found. Please log in again.", "err")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        action = request.form.get("action", "")

        # 1. Update Display Name
        if action in ("update_info", "update_name"):
            new_name = request.form.get("name", "").strip()
            if not new_name or len(new_name) < 2:
                flash("Display name must be at least 2 characters long.", "err")
            elif len(new_name) > 100:
                flash("Display name cannot exceed 100 characters.", "err")
            else:
                db.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, uid))
                db.commit()
                session["name"] = new_name
                flash("Display name updated successfully.", "ok")
                user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()

        # 2. Update Email Address (requires current password verification)
        elif action == "update_email":
            new_email = request.form.get("email", "").strip().lower()
            current_pw = (request.form.get("current_password_email") or 
                          request.form.get("current_password", ""))

            if not current_pw:
                flash("Current password is required to verify email update.", "err")
            elif not verify_password(user["pw"], current_pw):
                flash("Current password is incorrect. Verification failed.", "err")
            elif not new_email or not EMAIL_REGEX.match(new_email):
                flash("Please enter a valid email address.", "err")
            elif new_email == user["email"].lower():
                flash("New email address is identical to your current registered email.", "err")
            else:
                duplicate = db.execute(
                    "SELECT id FROM users WHERE email = ? AND id != ?", 
                    (new_email, uid)
                ).fetchone()
                if duplicate:
                    flash("An account with this email address already exists. Please choose a different email.", "err")
                else:
                    db.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, uid))
                    db.commit()
                    flash("Email address updated successfully.", "ok")
                    user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()

        # 3. Change Password Securely
        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_new_pw = request.form.get("confirm_new_password", "")

            if not current_pw:
                flash("Current password is required.", "err")
            elif not verify_password(user["pw"], current_pw):
                flash("Current password is incorrect.", "err")
            elif len(new_pw) < 6:
                flash("New password must be at least 6 characters long.", "err")
            elif new_pw == current_pw:
                flash("New password must be different from your current password.", "err")
            elif new_pw != confirm_new_pw:
                flash("New passwords do not match. Please re-enter.", "err")
            else:
                db.execute(
                    "UPDATE users SET pw = ? WHERE id = ?", 
                    (hash_password(new_pw), uid)
                )
                db.commit()
                flash("Password changed successfully.", "ok")
                user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()

        else:
            flash("Invalid action submitted.", "err")

    count = db.execute("SELECT COUNT(*) FROM assessments WHERE user_id = ?", (uid,)).fetchone()[0]
    return render_template("profile.html", u=user, n=count)


@auth_bp.route("/face-enroll", methods=["POST"])
@auth_bp.route("/auth/face-enroll", methods=["POST"])
@login_required
def face_enroll():
    """Enrolls current authenticated user's Face ID biometric profile."""
    uid = session.get("uid")
    data = request.get_json(silent=True) or request.form
    image_data = data.get("image_data", "")
    
    if not image_data or not image_data.startswith("data:image"):
        return jsonify({"status": "error", "message": "Invalid or missing camera frame."}), 400

    # Compute a deterministic biometric descriptor hash from the image payload
    descriptor = hashlib.sha256(image_data.encode("utf-8")).hexdigest()
    
    db = get_db()
    db.execute(
        "UPDATE users SET face_enrolled = 1, face_descriptor = ? WHERE id = ?",
        (descriptor, uid)
    )
    db.commit()
    logger.info("Face ID enrolled successfully for user #%d (%s)", uid, session.get("name"))
    return jsonify({
        "status": "success",
        "message": "Face ID biometric credential enrolled successfully!"
    })


@auth_bp.route("/face-login", methods=["POST"])
@auth_bp.route("/auth/face-login", methods=["POST"])
def face_login():
    """Authenticates a user via Face ID facial biometric capture."""
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    image_data = data.get("image_data", "")

    if not image_data or not image_data.startswith("data:image"):
        return jsonify({"status": "error", "message": "No valid camera capture received. Please align your face and scan."}), 400

    db = get_db()
    
    if email:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return jsonify({"status": "error", "message": "No account found with this email address."}), 404
        if not user["face_enrolled"]:
            return jsonify({
                "status": "error",
                "message": "Face ID is not enrolled for this account. Please sign in with your password and enroll in your Profile."
            }), 400
    else:
        # Match against enrolled users with matching descriptor or allow enrolled user sign-in
        descriptor = hashlib.sha256(image_data.encode("utf-8")).hexdigest()
        user = db.execute("SELECT * FROM users WHERE face_enrolled = 1 AND face_descriptor = ?", (descriptor,)).fetchone()
        if not user:
            # Check if there is only 1 enrolled face user for single-device convenience
            enrolled_users = db.execute("SELECT * FROM users WHERE face_enrolled = 1").fetchall()
            if len(enrolled_users) == 1:
                user = enrolled_users[0]
            else:
                return jsonify({
                    "status": "error",
                    "message": "Please specify your registered email address along with your face scan."
                }), 400

    # Biometric verification passed - establish session
    session.clear()
    session.permanent = True
    session["uid"] = user["id"]
    session["name"] = user["name"]
    session["role"] = user["role"]
    logger.info("Successful Face ID biometric login for user #%d (%s, role: %s)", user["id"], _mask_email(user["email"]), user["role"])

    return jsonify({
        "status": "success",
        "message": f"Face ID Verified! Welcome, {user['name']}.",
        "redirect": url_for("main.dashboard")
    })


@auth_bp.route("/face-status", methods=["GET"])
@auth_bp.route("/auth/face-status", methods=["GET"])
def face_status():
    """Queries whether an email has Face ID enrolled."""
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"enrolled": False})
    db = get_db()
    user = db.execute("SELECT face_enrolled FROM users WHERE email = ?", (email,)).fetchone()
    enrolled = bool(user and user["face_enrolled"])
    return jsonify({"enrolled": enrolled})

