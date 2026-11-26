"""
Generate High-Resolution, Publication-Grade Visual Diagrams for NutriRisk AI.
Renders all 10 academic diagrams specified in ARCHITECTURE_AND_TECHNICAL_DIAGRAMS.md:
  1. Overall System Architecture
  2. Data Flow Diagram (DFD) Level 0
  3. Data Flow Diagram (DFD) Level 1
  4. Machine Learning Workflow
  5. Use Case Diagram
  6. Database Entity-Relationship (ER) Diagram
  7. User Assessment Sequence Diagram
  8. Activity Diagram
  9. Model Training Pipeline
  10. Risk Prediction & Explainability (XAI) Workflow
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ArrowStyle

OUT_DIR = r"D:\MAJOR PROJECT\reports\diagrams"
os.makedirs(OUT_DIR, exist_ok=True)

# Color Palette (Matching Clinical Design System)
C_PRIMARY = "#0f766e"      # Deep Teal
C_PRIMARY_LIGHT = "#ccfbf1"# Light Teal Tint
C_PRIMARY_BG = "#f0fdfa"   # Soft Aqua Background
C_SLATE = "#0f172a"        # Dark Slate
C_TEXT = "#1e293b"         # Charcoal Text
C_MUTED = "#64748b"        # Muted Slate
C_BORDER = "#94a3b8"       # Border Grey
C_WHITE = "#ffffff"
C_EMERALD = "#10b981"      # Low Risk Green
C_AMBER = "#f59e0b"        # Moderate Risk Orange
C_CRIMSON = "#dc2626"      # High Risk Red
C_CONTAINER = "#f8fafc"    # Light Container Grey
C_BOX_HEADER = "#1e293b"


def setup_canvas(width=11, height=7, title=""):
    """Sets up a clean canvas with title banner."""
    fig, ax = plt.subplots(figsize=(width, height), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(C_WHITE)

    # Title Banner
    if title:
        banner = FancyBboxPatch(
            (2, 92), 96, 6.5,
            boxstyle="round,pad=0.2,rounding_size=0.8",
            facecolor=C_PRIMARY,
            edgecolor="none"
        )
        ax.add_patch(banner)
        ax.text(
            50, 95.25, title,
            ha="center", va="center",
            fontsize=12, fontweight="bold",
            color=C_WHITE, fontfamily="sans-serif"
        )
    return fig, ax


def add_card(ax, x, y, w, h, title, items=None, bg=C_WHITE, border=C_PRIMARY, title_bg=None, text_color=C_TEXT, fontsize=8):
    """Draws a rounded card box with optional header title and item bullets."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3,rounding_size=0.8",
        facecolor=bg,
        edgecolor=border,
        linewidth=1.2
    )
    ax.add_patch(box)

    curr_y = y + h - 2.2
    if title:
        if title_bg:
            # Header pill
            h_box = FancyBboxPatch(
                (x, y + h - 3.8), w, 3.8,
                boxstyle="round,pad=0.1,rounding_size=0.6",
                facecolor=title_bg,
                edgecolor="none"
            )
            ax.add_patch(h_box)
            ax.text(x + w / 2, y + h - 1.9, title, ha="center", va="center", fontsize=fontsize + 0.5, fontweight="bold", color=C_WHITE)
            curr_y = y + h - 5.2
        else:
            ax.text(x + w / 2, curr_y, title, ha="center", va="center", fontsize=fontsize + 0.5, fontweight="bold", color=border)
            curr_y -= 2.6

    if items:
        for item in items:
            ax.text(x + 1.5, curr_y, item, ha="left", va="center", fontsize=fontsize, color=text_color)
            curr_y -= 2.2


def add_arrow(ax, x1, y1, x2, y2, label="", color=C_PRIMARY, lw=1.5, curve=0):
    """Draws a directional arrow with optional centered text label."""
    if curve == 0:
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=lw,
                mutation_scale=12
            )
        )
    else:
        connectionstyle = f"arc3,rad={curve}"
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=lw,
                connectionstyle=connectionstyle,
                mutation_scale=12
            )
        )
    if label:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2 + (1.2 if curve == 0 else 2.0)
        ax.text(mid_x, mid_y, label, ha="center", va="center", fontsize=7, fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.2", facecolor=C_WHITE, edgecolor=C_BORDER, lw=0.5))


def add_cylinder(ax, x, y, w, h, title, items=None, bg=C_PRIMARY_BG, border=C_PRIMARY):
    """Draws a cylinder-like database container."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3,rounding_size=1.5",
        facecolor=bg,
        edgecolor=border,
        linewidth=1.4
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h - 2.2, f"💾 {title}", ha="center", va="center", fontsize=8.5, fontweight="bold", color=border)
    if items:
        curr_y = y + h - 5.0
        for item in items:
            ax.text(x + 1.5, curr_y, item, ha="left", va="center", fontsize=7.5, color=C_TEXT)
            curr_y -= 2.0


# ==============================================================================
# Diagram 1: Overall System Architecture
# ==============================================================================
def generate_diagram_1():
    fig, ax = setup_canvas(11.5, 7.5, "Diagram 1: NutriRisk AI — Overall 4-Tier System Architecture")

    # Tier 1: Client Layer
    add_card(ax, 3, 62, 28, 26, "Tier 1: Client Interface Layer", [
        "• Responsive Web Browser (Mobile / Desktop)",
        "• Bootstrap 5 Offline Clinical UI",
        "• Client-side Live BMI Calculator (JS)",
        "• Under-18 Pediatric Alert Modal (WHO)",
        "• Face ID Webcam Biometric Capture",
        "• Interactive Chart.js Visualizations"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY)

    # Tier 2: Presentation & Routing Layer (Flask)
    add_card(ax, 36, 62, 30, 26, "Tier 2: Presentation & Routing (Flask)", [
        "• Application Factory (create_app)",
        "• 5 Modular Blueprints (auth, predict, etc.)",
        "• Salted Scrypt / Argon2 Password Hashing",
        "• Face ID Biometric Verification Handler",
        "• Defensive CSRF & HTTP Security Headers",
        "• Role-Based Access Control (@admin_required)"
    ], bg="#f8fafc", border=C_SLATE, title_bg=C_SLATE)

    # Tier 3: ML Pipeline & Explainability Engine
    add_card(ax, 70, 62, 27, 26, "Tier 3: ML Inference & XAI", [
        "• Feature Engine: BMI = wt/(ht/100)²",
        "• Preprocessing (ColumnTransformer)",
        "• Median/Mode Impute + OneHotEncoder",
        "• Serialized XGBoost Model (model.joblib)",
        "• 3-Tier Multi-Class Probability Engine",
        "• Local Occlusion XAI Explainer (Factors)"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY)

    # Tier 4: Data Persistence & Report Generation
    add_card(ax, 15, 10, 36, 40, "Tier 4A: SQLite 3 Persistence (WAL Mode)", [
        "• users (id, name, email, pw, role, face_enrolled)",
        "• assessments (patient, 11 features, bmi, risk)",
        "• model_metadata (version, metrics, is_active)",
        "• admin_audit_logs (admin_id, action, timestamp)",
        "• Foreign Key Cascades & Strict Isolation",
        "• Non-Destructive Auto-Schema Migrations"
    ], bg="#fdfbf7", border=C_AMBER, title_bg=C_AMBER)

    add_card(ax, 56, 10, 32, 40, "Tier 4B: Clinical PDF Engine & Reporting", [
        "• ReportLab 5.0 ISO A4 Vector PDF Builder",
        "• Institutional Header & Accreditation Badges",
        "• Demographic & Nutritional Inputs Table",
        "• Multi-Class Probability Distributions",
        "• XAI Directional Attributions (▲ Risk / ▼ Prot)",
        "• Clinical Next-Step Protocols & Legal Disclaimer"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY)

    # Inter-tier arrows
    add_arrow(ax, 31, 75, 36, 75, "HTTPS / JSON", C_PRIMARY)
    add_arrow(ax, 66, 75, 70, 75, "Feature Vector", C_PRIMARY)
    add_arrow(ax, 50, 62, 40, 50, "SQL Transact", C_AMBER)
    add_arrow(ax, 75, 62, 70, 50, "Inference Context", C_PRIMARY)
    add_arrow(ax, 51, 30, 56, 30, "Archived Data", C_MUTED)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag01_system_architecture.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 2: DFD Level 0 (Context Diagram)
# ==============================================================================
def generate_diagram_2():
    fig, ax = setup_canvas(11, 7, "Diagram 2: Data Flow Diagram (DFD) Level 0 — Context Level")

    # Central System
    center = FancyBboxPatch((35, 30), 30, 40, boxstyle="circle,pad=0.5", facecolor=C_PRIMARY_BG, edgecolor=C_PRIMARY, linewidth=2)
    ax.add_patch(center)
    ax.text(50, 54, "0.0\nNutriRisk AI", ha="center", va="center", fontsize=13, fontweight="bold", color=C_PRIMARY)
    ax.text(50, 43, "Predictive Malnutrition\nStratification &\nClinical Decision System", ha="center", va="center", fontsize=8.5, color=C_TEXT)

    # External Entity 1: Clinician / User
    add_card(ax, 4, 34, 22, 32, "Clinician / Health Worker", [
        "• Patient Demographic Data",
        "• Anthropometric Readings",
        "• Dietary Diversity Inputs",
        "• Face ID Biometric Frames",
        "• Login Credentials",
        "• Filter / Search Queries"
    ], bg=C_WHITE, border=C_SLATE, title_bg=C_SLATE, fontsize=7.5)

    # External Entity 2: Administrator
    add_card(ax, 74, 34, 22, 32, "Hospital Administrator", [
        "• Admin Authentication",
        "• Account Provisioning Directives",
        "• Role Privilege Elevation",
        "• Model Version Audit Requests",
        "• System Audit Log Queries",
        "• Telemetry Ingestion Controls"
    ], bg=C_WHITE, border=C_SLATE, title_bg=C_SLATE, fontsize=7.5)

    # Data Flows to/from Clinician
    add_arrow(ax, 26, 56, 38, 56, "1. Patient Demographics & Diet", C_PRIMARY)
    add_arrow(ax, 38, 48, 26, 48, "2. Risk Stratification & XAI", C_EMERALD)
    add_arrow(ax, 38, 40, 26, 40, "3. ISO A4 PDF Assessment Report", C_PRIMARY)

    # Data Flows to/from Administrator
    add_arrow(ax, 74, 55, 62, 55, "1. User Role & System Controls", C_AMBER)
    add_arrow(ax, 62, 46, 74, 46, "2. Cohort Analytics & Trends", C_PRIMARY)
    add_arrow(ax, 62, 38, 74, 38, "3. Model Metadata & Audit Logs", C_SLATE)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag02_dfd_level_0.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 3: DFD Level 1 (Detailed Subsystems & Datastores)
# ==============================================================================
def generate_diagram_3():
    fig, ax = setup_canvas(11.5, 7.5, "Diagram 3: Data Flow Diagram (DFD) Level 1 — Decomposed Workflow")

    # Processes
    add_card(ax, 5, 66, 20, 18, "1.0 Auth & Face ID", [
        "• Scrypt PW Validation",
        "• Biometric Descriptor Hash",
        "• Session Cookie Token"
    ], bg=C_WHITE, border=C_SLATE, title_bg=C_SLATE, fontsize=7)

    add_card(ax, 30, 66, 20, 18, "2.0 Input Validation", [
        "• Age Boundary (18-90)",
        "• Under-18 Pediatric Alert",
        "• Height (120-220cm)",
        "• Weight (30-180kg)"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7)

    add_card(ax, 55, 66, 20, 18, "3.0 BMI Engineering", [
        "• Derive BMI Feature:",
        "  BMI = wt / (ht/100)²",
        "• Format 12-Feature Matrix"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7)

    add_card(ax, 78, 66, 18, 18, "4.0 ML Inference", [
        "• ColumnTransformer",
        "• Impute + Scale + OneHot",
        "• XGBoost Execution",
        "• Multi-Class Probabilities"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7)

    add_card(ax, 78, 22, 18, 24, "5.0 XAI Attribution", [
        "• Local Occlusion Engine",
        "• Occlude with Medians",
        "• Δ Probability Shift",
        "• Contributing Factors (▲/▼)"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7)

    add_card(ax, 42, 22, 24, 24, "6.0 Result & PDF Engine", [
        "• Stratification Tier Mapping",
        "• Confidence Scoring",
        "• Recommended Next Steps",
        "• ReportLab Vector PDF Builder"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7)

    # Datastores
    add_cylinder(ax, 5, 22, 24, 24, "SQLite Database (WAL)", [
        "D1: users (auth & face)",
        "D2: assessments (screenings)",
        "D3: model_metadata (version)",
        "D4: admin_audit_logs"
    ])

    # Connecting Arrows
    add_arrow(ax, 15, 66, 15, 46, "D1 Read/Write", C_SLATE)
    add_arrow(ax, 25, 75, 30, 75, "Auth Token", C_PRIMARY)
    add_arrow(ax, 50, 75, 55, 75, "Valid Data", C_PRIMARY)
    add_arrow(ax, 75, 75, 78, 75, "12-dim Vector", C_PRIMARY)
    add_arrow(ax, 87, 66, 87, 46, "Probabilities", C_PRIMARY)
    add_arrow(ax, 78, 34, 66, 34, "XAI Drivers", C_PRIMARY)
    add_arrow(ax, 42, 34, 29, 34, "D2 Persist", C_AMBER)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag03_dfd_level_1.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 4: Machine Learning Workflow
# ==============================================================================
def generate_diagram_4():
    fig, ax = setup_canvas(11.5, 7.5, "Diagram 4: NutriRisk AI — End-to-End Machine Learning Workflow")

    steps = [
        ("Phase 1: Ingestion", [
            "• 6,000 Synthetic Cohort",
            "• WHO & FAO Benchmarks",
            "• 11 Clinical Indicators"
        ], C_PRIMARY_BG, C_PRIMARY),
        ("Phase 2: Preprocessing", [
            "• BMI = wt / (ht/100)²",
            "• Missing Value Profiling",
            "• Outlier Guardrails"
        ], C_CONTAINER, C_SLATE),
        ("Phase 3: Pipeline Split", [
            "• 80:20 Train-Test Split",
            "• Stratified Sampling",
            "• ColumnTransformer Fit"
        ], C_PRIMARY_BG, C_PRIMARY),
        ("Phase 4: Benchmarking", [
            "• 5 Algorithms Evaluated",
            "• 5-Fold Stratified CV",
            "• Logistic Reg -> XGBoost"
        ], C_CONTAINER, C_AMBER),
        ("Phase 5: Best Model", [
            "• XGBoost Selected",
            "• 74.0% Test Accuracy",
            "• Macro F1: 0.7315",
            "• ROC-AUC: 0.8910"
        ], C_PRIMARY_BG, C_EMERALD),
        ("Phase 6: Deployment", [
            "• model.joblib Serialization",
            "• In-Memory Fast Cache",
            "• Real-Time Inference (<45ms)"
        ], C_PRIMARY_BG, C_PRIMARY),
    ]

    x_positions = [4, 20, 36, 52, 68, 84]
    for i, (title, items, bg, border) in enumerate(steps):
        add_card(ax, x_positions[i], 42, 13, 44, title, items, bg=bg, border=border, fontsize=6.8)
        if i < len(steps) - 1:
            add_arrow(ax, x_positions[i] + 13, 64, x_positions[i+1], 64, "", border, lw=1.6)

    # Bottom Explainability & Governance Box
    add_card(ax, 10, 10, 80, 24, "Phase 7: Explainable AI (XAI) & Clinical Governance", [
        "• Local Occlusion Feature Attribution: Evaluates individual patient inputs against population medians/modes.",
        "• Feature Directionality: Explicitly maps factors to Risk-Increasing (▲) vs Protective (▼) clinical impacts.",
        "• Calibrated Multi-Class Probabilities: P(Low Risk), P(Moderate Risk), P(High Risk) summing strictly to 1.0.",
        "• High-Risk Recall Safety Guard: False negative rate rigorously bounded at 2.12% (6/283) on test cohort."
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7.8)

    add_arrow(ax, 90, 42, 80, 34, "XAI Inference", C_PRIMARY, curve=0.2)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag04_ml_workflow.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 5: Use Case Diagram
# ==============================================================================
def generate_diagram_5():
    fig, ax = setup_canvas(11, 7.5, "Diagram 5: NutriRisk AI — Unified System Use Case Diagram")

    # Boundary Box
    system_box = FancyBboxPatch((28, 8), 44, 80, boxstyle="round,pad=0.5,rounding_size=1.0", facecolor="#ffffff", edgecolor=C_PRIMARY, linewidth=1.5)
    ax.add_patch(system_box)
    ax.text(50, 85, "NutriRisk AI Application Boundary", ha="center", va="center", fontsize=10, fontweight="bold", color=C_PRIMARY)

    # Actor 1: Clinician (Left)
    add_card(ax, 3, 38, 20, 28, "👤 Clinician / Health Worker", [
        "Primary Operational Actor",
        "• Frontend User Interface",
        "• Patient Consultations",
        "• Community Screening"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7.5)

    # Actor 2: Administrator (Right)
    add_card(ax, 77, 38, 20, 28, "🛡️ Hospital Administrator", [
        "System Governance Actor",
        "• IT & Clinical Governance",
        "• Model Telemetry Audits",
        "• Staff Account Oversight"
    ], bg="#f8fafc", border=C_SLATE, title_bg=C_SLATE, fontsize=7.5)

    # Use Cases inside Boundary
    use_cases = [
        (50, 77, "UC1: Register & Login (Password / Face ID)"),
        (50, 69, "UC2: Dynamic Nutritional Assessment (BMI Calc)"),
        (50, 61, "UC3: Under-18 Scope Boundary Alert Trigger"),
        (50, 53, "UC4: Multi-Class Risk Stratification & Confidence"),
        (50, 45, "UC5: Inspect Contributing XAI Risk Factors"),
        (50, 37, "UC6: Download ISO A4 Vector PDF Report"),
        (50, 29, "UC7: Batch Patient CSV Screening (/batch)"),
        (50, 21, "UC8: View Epidemiological Analytics (/analytics)"),
        (50, 13, "UC9: Manage Accounts, Audits & Models (/admin)"),
    ]

    for ux, uy, ulabel in use_cases:
        p = FancyBboxPatch((ux - 19, uy - 2.6), 38, 5.2, boxstyle="round,pad=0.2,rounding_size=2.0", facecolor=C_PRIMARY_BG, edgecolor=C_BORDER, linewidth=0.8)
        ax.add_patch(p)
        ax.text(ux, uy, ulabel, ha="center", va="center", fontsize=7.5, fontweight="bold", color=C_TEXT)

    # Clinician Associations (UC1 to UC7, UC8)
    for uy in [77, 69, 61, 53, 45, 37, 29, 21]:
        ax.plot([23, 31], [52, uy], color=C_PRIMARY, lw=1.0, linestyle="--")

    # Admin Associations (UC1, UC8, UC9)
    for uy in [77, 21, 13]:
        ax.plot([77, 69], [52, uy], color=C_SLATE, lw=1.0, linestyle="--")

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag05_use_case.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 6: Database ER Diagram
# ==============================================================================
def generate_diagram_6():
    fig, ax = setup_canvas(11.5, 7.5, "Diagram 6: SQLite Relational Database Entity-Relationship (ER) Diagram")

    # Entity 1: USERS
    add_card(ax, 5, 46, 26, 40, "USERS (Table)", [
        "🔑 id: INTEGER PRIMARY KEY AUTOINC",
        "• name: TEXT NOT NULL",
        "• email: TEXT UNIQUE NOT NULL",
        "• pw: TEXT NOT NULL (Scrypt hash)",
        "• role: TEXT ('admin' | 'user')",
        "• created: TIMESTAMP NOT NULL",
        "• face_enrolled: INTEGER DEFAULT 0",
        "• face_descriptor: TEXT DEFAULT ''"
    ], bg="#f8fafc", border=C_SLATE, title_bg=C_SLATE, fontsize=7.5)

    # Entity 2: ASSESSMENTS
    add_card(ax, 46, 10, 48, 76, "ASSESSMENTS (Table)", [
        "🔑 id: INTEGER PRIMARY KEY AUTOINCREMENT",
        "🔗 user_id: INTEGER NOT NULL (FK -> users.id ON DELETE CASCADE)",
        "• patient_name: TEXT NOT NULL",
        "• age: INTEGER NOT NULL (Enforced 18-90)",
        "• sex: TEXT ('Male' | 'Female')",
        "• height_cm: REAL NOT NULL",
        "• weight_kg: REAL NOT NULL",
        "• bmi: REAL NOT NULL (Calculated: wt / (ht/100)²)",
        "• food_groups: INTEGER (Dietary Diversity: 1-10)",
        "• meals_per_day: INTEGER (1-6)",
        "• activity: TEXT ('Sedentary' | 'Moderate' | 'Active')",
        "• income: TEXT ('Low' | 'Middle' | 'High')",
        "• education: TEXT ('None' | 'Primary' | 'Secondary' | 'Tertiary')",
        "• residence: TEXT ('Urban' | 'Rural')",
        "• recent_illness: TEXT ('Yes' | 'No')",
        "• risk_tier: TEXT ('Low Risk' | 'Moderate Risk' | 'High Risk')",
        "• confidence: REAL (Probability of top class)",
        "• probabilities: TEXT (JSON: Low, Mod, High probabilities)",
        "• factors: TEXT (JSON: Local XAI feature attributions)",
        "• model_version: TEXT ('v1.0-xgboost')",
        "• created_at: TIMESTAMP NOT NULL"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, title_bg=C_PRIMARY, fontsize=7.2)

    # Entity 3: MODEL_METADATA
    add_card(ax, 5, 26, 26, 17, "MODEL_METADATA", [
        "🔑 id: INTEGER PRIMARY KEY",
        "• model_name: TEXT NOT NULL",
        "• model_version: TEXT ('v1.0-xgboost')",
        "• algorithm: TEXT ('XGBoost')",
        "• accuracy: 0.7400, f1: 0.7315",
        "• is_active: INTEGER DEFAULT 1"
    ], bg="#fefce8", border=C_AMBER, title_bg=C_AMBER, fontsize=7.0)

    # Entity 4: ADMIN_AUDIT_LOGS
    add_card(ax, 5, 8, 26, 15, "ADMIN_AUDIT_LOGS", [
        "🔑 id: INTEGER PRIMARY KEY",
        "🔗 admin_id: INTEGER (FK -> users.id)",
        "• action: TEXT NOT NULL",
        "• target_user_id: INTEGER",
        "• timestamp: TIMESTAMP NOT NULL"
    ], bg="#f8fafc", border=C_MUTED, title_bg=C_MUTED, fontsize=7.0)

    # Relationships
    add_arrow(ax, 31, 66, 46, 66, "1 : N (Cascade Delete)", C_PRIMARY, lw=1.8)
    add_arrow(ax, 18, 46, 18, 23, "1 : N (Audits)", C_MUTED, lw=1.2)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag06_database_er.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 7: User Assessment Sequence Diagram
# ==============================================================================
def generate_diagram_7():
    fig, ax = setup_canvas(11.5, 7.5, "Diagram 7: User Assessment Workflow Sequence Diagram")

    actors = [
        ("Clinician", 10),
        ("Web Browser", 28),
        ("Flask Route (/predict)", 48),
        ("ML Engine (XGBoost)", 68),
        ("SQLite DB (WAL)", 88)
    ]

    for label, x in actors:
        box = FancyBboxPatch((x - 7, 85), 14, 5, boxstyle="round,pad=0.2", facecolor=C_SLATE, edgecolor="none")
        ax.add_patch(box)
        ax.text(x, 87.5, label, ha="center", va="center", fontsize=7.5, fontweight="bold", color=C_WHITE)
        ax.plot([x, x], [12, 85], color=C_BORDER, lw=1.0, linestyle=":")

    # Sequential Messages
    messages = [
        (10, 28, 79, "1. Enters Demographics & Diet", C_PRIMARY),
        (28, 28, 73, "2. Live BMI Calc & Under-18 Check", C_AMBER),
        (28, 48, 67, "3. POST /predict (Form Data)", C_PRIMARY),
        (48, 48, 61, "4. Server Validation & Age Gate", C_SLATE),
        (48, 68, 55, "5. Preprocessing & XGBoost Inference", C_PRIMARY),
        (68, 68, 49, "6. Multi-Class Probabilities & XAI", C_PRIMARY),
        (68, 48, 43, "7. Stratified Risk Result + Factors", C_PRIMARY),
        (48, 88, 37, "8. INSERT INTO assessments", C_AMBER),
        (88, 48, 31, "9. Commit Confirmation (Record ID)", C_AMBER),
        (48, 28, 25, "10. HTTP 302 Redirect (/result/<id>)", C_PRIMARY),
        (28, 10, 19, "11. Displays Result, Probabilities & XAI", C_EMERALD),
        (10, 48, 14, "12. Optional: GET /download (PDF)", C_PRIMARY)
    ]

    for x1, x2, y, label, col in messages:
        if x1 == x2:
            # Self-call
            ax.annotate("", xy=(x1, y - 2), xytext=(x1, y), arrowprops=dict(arrowstyle="-|>", color=col, lw=1.2, connectionstyle="arc3,rad=-0.8"))
            ax.text(x1 + 1.5, y - 1, label, ha="left", va="center", fontsize=7, color=col, fontweight="bold")
        else:
            add_arrow(ax, x1, y, x2, y, "", col, lw=1.2)
            mid_x = (x1 + x2) / 2
            ax.text(mid_x, y + 1.2, label, ha="center", va="center", fontsize=7, color=col, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor=C_WHITE, edgecolor="none"))

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag07_sequence_diagram.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 8: Activity Diagram
# ==============================================================================
def generate_diagram_8():
    fig, ax = setup_canvas(11, 7.5, "Diagram 8: NutriRisk AI — Assessment Lifecycle Activity Diagram")

    # Start Node
    ax.add_patch(plt.Circle((10, 80), 2.2, facecolor=C_SLATE, edgecolor=C_PRIMARY, lw=1.5))
    ax.text(10, 75, "Start", ha="center", va="center", fontsize=8, fontweight="bold", color=C_SLATE)

    # Activity Nodes
    nodes = [
        (25, 80, "Clinician Logs In\n(PW or Face ID)"),
        (45, 80, "Navigate to\n/predict Assessment"),
        (65, 80, "Input Demographics\n& Nutritional Data"),
        (85, 80, "Live Client JS BMI\n& Under-18 Check"),
        (85, 52, "Age < 18 Years?"),
        (85, 24, "Show WHO Pediatric\nAlert Modal"),
        (55, 52, "Server Range Validation\n(18 <= Age <= 90)"),
        (30, 52, "ColumnTransformer\n& XGBoost Prediction"),
        (30, 24, "Compute Multi-Class\nProbabilities & XAI"),
        (55, 24, "Persist Record to\nSQLite (WAL Mode)"),
        (75, 24, "Display Result Page\n& Enable PDF Download")
    ]

    for x, y, label in nodes:
        if "Age < 18" in label:
            # Diamond decision
            diamond = patches.RegularPolygon((x, y), numVertices=4, radius=5.0, facecolor="#fefce8", edgecolor=C_AMBER, lw=1.5)
            ax.add_patch(diamond)
            ax.text(x, y, label, ha="center", va="center", fontsize=7.2, fontweight="bold", color=C_AMBER)
        else:
            box = FancyBboxPatch((x - 8.5, y - 4), 17, 8, boxstyle="round,pad=0.2,rounding_size=1.2", facecolor=C_PRIMARY_BG, edgecolor=C_PRIMARY, lw=1.2)
            ax.add_patch(box)
            ax.text(x, y, label, ha="center", va="center", fontsize=7.5, fontweight="bold", color=C_TEXT)

    # Connections
    add_arrow(ax, 12.2, 80, 16.5, 80, "", C_PRIMARY)
    add_arrow(ax, 33.5, 80, 36.5, 80, "", C_PRIMARY)
    add_arrow(ax, 53.5, 80, 56.5, 80, "", C_PRIMARY)
    add_arrow(ax, 73.5, 80, 76.5, 80, "", C_PRIMARY)
    add_arrow(ax, 85, 76, 85, 57, "Submit", C_PRIMARY)
    add_arrow(ax, 85, 47, 85, 28, "Yes (<18)", C_CRIMSON)
    add_arrow(ax, 80, 52, 63.5, 52, "No (Adult 18+)", C_EMERALD)
    add_arrow(ax, 46.5, 52, 38.5, 52, "Valid", C_PRIMARY)
    add_arrow(ax, 30, 48, 30, 28, "", C_PRIMARY)
    add_arrow(ax, 38.5, 24, 46.5, 24, "", C_PRIMARY)
    add_arrow(ax, 63.5, 24, 66.5, 24, "", C_PRIMARY)

    # End Node
    ax.add_patch(plt.Circle((95, 24), 2.2, facecolor=C_WHITE, edgecolor=C_PRIMARY, lw=1.5))
    ax.add_patch(plt.Circle((95, 24), 1.4, facecolor=C_PRIMARY))
    ax.text(95, 19, "End", ha="center", va="center", fontsize=8, fontweight="bold", color=C_PRIMARY)
    add_arrow(ax, 83.5, 24, 92.5, 24, "", C_PRIMARY)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag08_activity_diagram.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 9: Model Training Pipeline
# ==============================================================================
def generate_diagram_9():
    fig, ax = setup_canvas(11.5, 7.5, "Diagram 9: Machine Learning Training & Evaluation Pipeline")

    stages = [
        (4, 52, 17, 36, "1. Dataset Ingestion", [
            "• 6,000 Synthetic Samples",
            "• 11 Input Demographics",
            "• WHO / FAO Realistic Dist",
            "• Zero Synthetic Label Bias"
        ], C_PRIMARY_BG, C_PRIMARY),
        (24, 52, 17, 36, "2. Data Preparation", [
            "• BMI = wt / (ht/100)²",
            "• Missing Data Profiling",
            "• 80:20 Train-Test Split",
            "• Stratified Sampling"
        ], C_CONTAINER, C_SLATE),
        (44, 52, 17, 36, "3. Preprocessing", [
            "• ColumnTransformer",
            "• Median Impute (Numeric)",
            "• Mode Impute (Categorical)",
            "• StandardScaler & OneHot"
        ], C_PRIMARY_BG, C_PRIMARY),
        (64, 52, 17, 36, "4. 5-Fold Stratified CV", [
            "• 5 Model Benchmark:",
            "  - Logistic Reg (67.0%)",
            "  - Decision Tree (68.6%)",
            "  - Random Forest (72.1%)",
            "  - Gradient Boost (73.8%)"
        ], C_CONTAINER, C_AMBER),
        (84, 52, 14, 36, "5. XGBoost Tuner", [
            "• Best Model Chosen",
            "• Acc: 74.00%",
            "• Macro F1: 0.7315",
            "• ROC-AUC: 0.8910"
        ], C_PRIMARY_BG, C_EMERALD)
    ]

    for x, y, w, h, title, items, bg, border in stages:
        add_card(ax, x, y, w, h, title, items, bg=bg, border=border, fontsize=6.8)

    add_arrow(ax, 21, 70, 24, 70, "", C_PRIMARY)
    add_arrow(ax, 41, 70, 44, 70, "", C_PRIMARY)
    add_arrow(ax, 61, 70, 64, 70, "", C_PRIMARY)
    add_arrow(ax, 81, 70, 84, 70, "", C_PRIMARY)

    # Bottom Stage: Model Artifacts & Registration
    add_card(ax, 15, 12, 70, 28, "6. Model Serialization & Database Metadata Registration", [
        "• Export trained scikit-learn/XGBoost pipeline to model/model.joblib.",
        "• Record performance metrics (accuracy, macro F1, log-loss, ROC-AUC) into model/metrics.json.",
        "• Seed model version 'v1.0-xgboost' and hyperparameter stamps into SQLite model_metadata table.",
        "• Ensure Zero Data Leakage: Transformer fitted strictly on train fold, applied identically during inference."
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7.8)

    add_arrow(ax, 91, 52, 85, 40, "Artifact Export", C_PRIMARY, curve=0.2)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag09_training_pipeline.png"), dpi=240)
    plt.close(fig)


# ==============================================================================
# Diagram 10: Risk Prediction & Explainability Workflow
# ==============================================================================
def generate_diagram_10():
    fig, ax = setup_canvas(11.5, 7.5, "Diagram 10: Risk Prediction & Explainable AI (XAI) Occlusion Workflow")

    # Step 1: Input Vector
    add_card(ax, 4, 52, 17, 36, "Input Vector", [
        "• Age: 65, Sex: M",
        "• Ht: 168cm, Wt: 48kg",
        "• BMI: 17.0 (Underweight)",
        "• Meals: 2, Food Groups: 3",
        "• Illness: Yes, Activity: Sed"
    ], bg=C_CONTAINER, border=C_SLATE, fontsize=7.0)

    # Step 2: Transformer
    add_card(ax, 24, 52, 17, 36, "ColumnTransformer", [
        "• Standardizes numeric",
        "• One-hot encodes cats",
        "• Imputes missing values",
        "• Zero-leakage schema"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7.0)

    # Step 3: XGBoost Classifier
    add_card(ax, 44, 52, 17, 36, "XGBoost Classifier", [
        "• 100 Gradient Trees",
        "• Softmax Log-Odds",
        "• Argmax Decision Rule",
        "• Multi-Class Confidence"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7.0)

    # Step 4: Posterior Probabilities
    add_card(ax, 64, 52, 16, 36, "Probabilities", [
        "• P(Low): 0.08",
        "• P(Moderate): 0.22",
        "• P(High Risk): 0.70",
        "-> Outcome: High Risk",
        "-> Confidence: 70%"
    ], bg="#fef2f2", border=C_CRIMSON, title_bg=C_CRIMSON, fontsize=7.0)

    # Step 5: Occlusion Engine
    add_card(ax, 83, 52, 14, 36, "XAI Occlusion", [
        "• Replace each feature",
        "  with population baseline",
        "• Δ Risk Probability",
        "• Rank Top Contributors"
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7.0)

    add_arrow(ax, 21, 70, 24, 70, "", C_PRIMARY)
    add_arrow(ax, 41, 70, 44, 70, "", C_PRIMARY)
    add_arrow(ax, 61, 70, 64, 70, "", C_PRIMARY)
    add_arrow(ax, 80, 70, 83, 70, "", C_PRIMARY)

    # Bottom Stage: Clinical Attributions & Recommended Action
    add_card(ax, 10, 10, 80, 30, "Clinical Factor Attribution & Stratified Action Protocol", [
        "• Factor 1: Low BMI (17.0 kg/m²) -> +28% Contribution (▲ Primary Risk-Increasing Factor)",
        "• Factor 2: Recent Acute Illness -> +19% Contribution (▲ Risk-Increasing Factor)",
        "• Factor 3: Low Dietary Diversity (3 food groups) -> +14% Contribution (▲ Risk-Increasing Factor)",
        "• Factor 4: Primary Education -> -4% Contribution (▼ Mild Protective Factor)",
        "---------------------------------------------------------------------------------------------------------",
        "• Output Clinical Protocol: Urgent Nutritional Consultation • Oral Nutritional Supplements (ONS) Required",
        "• Follow-Up Interval: Weekly clinical review • Comprehensive micronutrient panel screening."
    ], bg=C_PRIMARY_BG, border=C_PRIMARY, fontsize=7.5)

    add_arrow(ax, 90, 52, 85, 40, "Attributions", C_PRIMARY, curve=0.2)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "diag10_prediction_xai_workflow.png"), dpi=240)
    plt.close(fig)


def main():
    print("=" * 70)
    print("NutriRisk AI: Generating 10 High-Resolution Visual Architecture Diagrams")
    print("=" * 70)
    generate_diagram_1()
    print("[OK] Diagram 1: Overall System Architecture")
    generate_diagram_2()
    print("[OK] Diagram 2: DFD Level 0 (Context Diagram)")
    generate_diagram_3()
    print("[OK] Diagram 3: DFD Level 1 (Decomposed Architecture)")
    generate_diagram_4()
    print("[OK] Diagram 4: Machine Learning Workflow")
    generate_diagram_5()
    print("[OK] Diagram 5: Use Case Diagram")
    generate_diagram_6()
    print("[OK] Diagram 6: Database ER Diagram")
    generate_diagram_7()
    print("[OK] Diagram 7: User Assessment Sequence Diagram")
    generate_diagram_8()
    print("[OK] Diagram 8: Activity Diagram")
    generate_diagram_9()
    print("[OK] Diagram 9: Model Training Pipeline")
    generate_diagram_10()
    print("[OK] Diagram 10: Risk Prediction & XAI Workflow")
    print("=" * 70)
    print("All 10 Diagrams Generated Successfully in:", OUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    main()
