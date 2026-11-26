import os
import logging
from flask import Flask, render_template, request, session
from nutririsk.config import Config
from nutririsk.db import init_db, close_db
from nutririsk.auth.routes import auth_bp
from nutririsk.routes.main import main_bp
from nutririsk.routes.assessment import assessment_bp
from nutririsk.routes.analytics import analytics_bp
from nutririsk.routes.admin import admin_bp
from nutririsk.security import init_csrf_protection, add_security_headers

logger = logging.getLogger("nutririsk")


def create_app(config_class=Config):
    """
    Application factory pattern for NutriRisk AI.
    Configures database, registers modular blueprints, enables defensive security headers,
    initializes CSRF protection, and sets up custom error handlers (Prompt 21).
    """
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    if isinstance(config_class, dict):
        app.config.from_object(Config)
        app.config.update(config_class)
    else:
        app.config.from_object(config_class)
    
    # Configure session security defaults
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    
    # Initialize database tables
    with app.app_context():
        init_db(app)
        
    # Register teardown function for database connection
    app.teardown_appcontext(close_db)

    # Initialize Cryptographic CSRF Protection (Prompt 21 Item 2)
    init_csrf_protection(app)

    # Attach HTTP Defensive Security Headers (Prompt 21 Item 14)
    @app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_bp)
    
    # Global template context processor
    @app.context_processor
    def inject_global_context():
        return {
            "DISCLAIMER": app.config.get("DISCLAIMER")
        }
        
    # ─────────────────────────────────────────────────────────────────────────
    # Custom Clinical Error Handlers (Prompt 21 Item 9)
    # ─────────────────────────────────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        error_msg = getattr(e, "description", None)
        return render_template("errors/400.html", error_message=error_msg), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(
            "Unhandled 500 error on %s %s: %s",
            request.method,
            request.path,
            e,
            exc_info=True
        )
        return render_template("errors/500.html"), 500

    return app
