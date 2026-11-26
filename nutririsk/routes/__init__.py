"""Routes package for NutriRisk AI."""
from nutririsk.routes.main import main_bp
from nutririsk.routes.assessment import assessment_bp
from nutririsk.routes.analytics import analytics_bp
from nutririsk.routes.admin import admin_bp

__all__ = ["main_bp", "assessment_bp", "analytics_bp", "admin_bp"]
