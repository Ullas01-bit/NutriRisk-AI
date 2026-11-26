"""
Administrative Management & System Oversight Module (Prompt 17).
Provides:
  - User directory oversight and access governance.
  - Role promotion / demotion with privilege escalation prevention.
  - User account deletion with self-deletion safeguards.
  - System-wide risk distribution and screening activity charts.
  - Dataset provenance, licensing, and benchmark disclosure.
  - Model architecture, 5-fold CV training metrics, and artifact versioning.
  - Server runtime, database health, and library environment telemetry.
  - Persistent administrative action audit trail.
"""
import os
import sys
import json
import sqlite3
import importlib.metadata
from datetime import datetime
from typing import Optional, Dict, Any
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, abort, jsonify, current_app
)
from nutririsk.db import get_db, log_admin_action, get_active_model_metadata
from nutririsk.auth.utils import admin_required
from nutririsk.ml.features import LABELS
from nutririsk.ml.data_validation import load_dataset_metadata
from nutririsk.routes.main import load_metrics
from nutririsk.routes.analytics import calculate_statistics

admin_bp = Blueprint("admin", __name__)


def get_application_telemetry(db_path: str) -> Dict[str, Any]:
    """Inspects environment, runtime versions, and database file telemetry."""
    db_size_kb = 0.0
    if os.path.exists(db_path):
        db_size_kb = round(os.path.getsize(db_path) / 1024.0, 1)

    def _pkg_ver(pkg: str) -> str:
        try:
            return importlib.metadata.version(pkg)
        except Exception:
            return "N/A"

    return {
        "python_version": sys.version.split()[0],
        "flask_version": _pkg_ver("flask"),
        "sklearn_version": _pkg_ver("scikit-learn"),
        "xgboost_version": _pkg_ver("xgboost"),
        "shap_version": _pkg_ver("shap"),
        "db_path": os.path.basename(db_path),
        "db_size_kb": db_size_kb,
        "system_status": "Healthy / Operational",
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@admin_bp.route("/admin")
@admin_required
def admin():
    """
    Administrative oversight console.
    Compiles user directory, system analytics, dataset provenance,
    active model telemetry, and immutable audit logs.
    """
    db = get_db()
    db_path = current_app.config.get("DATABASE_PATH", "nutririsk.db")

    # 1. Registered User Directory (excluding password hashes for privacy)
    users = db.execute("""
        SELECT u.id, u.name, u.email, u.role, u.created,
               (SELECT COUNT(*) FROM assessments WHERE user_id = u.id) as n
        FROM users u
        ORDER BY u.id ASC
    """).fetchall()

    # 2. System-wide Global Assessment Statistics & Risk Breakdown
    global_stats = calculate_statistics()

    # 3. Recent System Assessments (Latest 10)
    recent_assessments = db.execute("""
        SELECT a.id, a.created, a.risk, a.confidence, a.bmi, u.name as user_name
        FROM assessments a
        JOIN users u ON u.id = a.user_id
        ORDER BY a.id DESC
        LIMIT 10
    """).fetchall()

    # 4. Model Training Metrics & Model Metadata Record
    metrics = load_metrics()
    active_meta = get_active_model_metadata(db)

    # 5. Dataset Provenance Metadata
    dataset_meta = load_dataset_metadata()

    # 6. Telemetry & Environment Info
    telemetry = get_application_telemetry(db_path)

    # 7. Administrative Action Audit Trail (Latest 20)
    audit_logs = db.execute("""
        SELECT id, admin_name, action, target_user_id, details, created_at
        FROM admin_audit_logs
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    return render_template(
        "admin.html",
        users=users,
        recent=recent_assessments,
        s=global_stats,
        m=metrics,
        labels=LABELS,
        active_meta=active_meta,
        dataset_meta=dataset_meta,
        telemetry=telemetry,
        audit_logs=audit_logs
    )


@admin_bp.route("/admin/user/<int:uid>/role", methods=["POST"])
@admin_required
def change_user_role(uid: int):
    """
    Updates a user's role (promote to admin or demote to user).
    Includes privilege escalation prevention and self-demotion protection.
    """
    db = get_db()
    current_admin_id = session["uid"]
    current_admin_name = session.get("name", "Admin")

    target_user = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (uid,)).fetchone()
    if not target_user:
        flash("Target user not found.", "err")
        return redirect(url_for("admin.admin"))

    new_role = request.form.get("role", "").strip().lower()
    if new_role not in ["user", "admin"]:
        flash("Invalid role specified. Supported roles are 'user' and 'admin'.", "err")
        return redirect(url_for("admin.admin"))

    # Security Rule 1: Admin cannot demote their own active session
    if uid == current_admin_id and new_role != "admin":
        flash("Privilege protection: You cannot demote your own administrator account.", "err")
        return redirect(url_for("admin.admin"))

    # Security Rule 2: Cannot demote the sole administrator in the system
    if target_user["role"] == "admin" and new_role == "user":
        admin_count = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        if admin_count <= 1:
            flash("System safeguard: Cannot demote the sole administrator in the system.", "err")
            return redirect(url_for("admin.admin"))

    # Update role
    db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, uid))
    db.commit()

    # Record administrative action in audit log
    action_label = f"ROLE_{new_role.upper()}"
    log_details = f"Changed role of user #{uid} ({target_user['name']} <{target_user['email']}>) from '{target_user['role']}' to '{new_role}'"
    log_admin_action(
        db=db,
        admin_id=current_admin_id,
        admin_name=current_admin_name,
        action=action_label,
        target_user_id=uid,
        details=log_details
    )

    flash(f"User #{uid} ({target_user['name']}) role updated to '{new_role}'.", "ok")
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/user/<int:uid>/delete", methods=["POST"])
@admin_required
def delete_user(uid: int):
    """
    Deletes a user account and cascades removal of their assessments.
    Enforces self-deletion and sole-admin safeguards.
    """
    db = get_db()
    current_admin_id = session["uid"]
    current_admin_name = session.get("name", "Admin")

    target_user = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (uid,)).fetchone()
    if not target_user:
        flash("Target user account not found.", "err")
        return redirect(url_for("admin.admin"))

    # Security Rule 1: Admin cannot delete their own account
    if uid == current_admin_id:
        flash("Self-deletion blocked: You cannot delete your own active administrator account.", "err")
        return redirect(url_for("admin.admin"))

    # Security Rule 2: Cannot delete the sole administrator
    if target_user["role"] == "admin":
        admin_count = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        if admin_count <= 1:
            flash("System safeguard: Cannot delete the sole administrator account.", "err")
            return redirect(url_for("admin.admin"))

    # Execute deletion (assessments table cascades deletion via FK)
    db.execute("DELETE FROM users WHERE id = ?", (uid,))
    db.commit()

    # Record in audit log
    log_details = f"Deleted user account #{uid} ({target_user['name']} <{target_user['email']}>)"
    log_admin_action(
        db=db,
        admin_id=current_admin_id,
        admin_name=current_admin_name,
        action="USER_DELETED",
        target_user_id=uid,
        details=log_details
    )

    flash(f"User account #{uid} ({target_user['name']}) and associated assessments have been deleted.", "ok")
    return redirect(url_for("admin.admin"))
