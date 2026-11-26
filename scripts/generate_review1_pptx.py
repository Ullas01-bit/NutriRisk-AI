import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck(output_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Professional Color Palette
    NAVY = RGBColor(15, 23, 42)        # #0F172A
    TEAL = RGBColor(13, 148, 136)      # #0D9488
    DARK_TEAL = RGBColor(15, 118, 110) # #0F766E
    SLATE = RGBColor(71, 85, 105)      # #475569
    LIGHT_BG = RGBColor(248, 250, 252) # #F8FAFC
    WHITE = RGBColor(255, 255, 255)
    BORDER_CLR = RGBColor(226, 232, 240)
    GOLD = RGBColor(217, 119, 6)

    def add_header_footer(slide, title_text, slide_num_str):
        # Top banner background
        top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.05))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = NAVY
        top_bar.line.fill.background()

        # Accent stripe
        accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.05), Inches(13.333), Inches(0.06))
        accent.fill.solid()
        accent.fill.fore_color.rgb = TEAL
        accent.line.fill.background()

        # Title text
        tx = slide.shapes.add_textbox(Inches(0.8), Inches(0.18), Inches(11.7), Inches(0.75))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = "Calibri"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = WHITE

        # Footer banner
        bot_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(6.95), Inches(13.333), Inches(0.55))
        bot_bar.fill.solid()
        bot_bar.fill.fore_color.rgb = RGBColor(241, 245, 249)
        bot_bar.line.fill.background()

        # Footer line
        f_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(6.92), Inches(13.333), Inches(0.03))
        f_line.fill.solid()
        f_line.fill.fore_color.rgb = BORDER_CLR
        f_line.line.fill.background()

        # Footer left text
        tx_f = slide.shapes.add_textbox(Inches(0.8), Inches(6.98), Inches(8.5), Inches(0.45))
        tf_f = tx_f.text_frame
        p_f = tf_f.paragraphs[0]
        p_f.text = "Dept. of CSE, School of Engineering — Dayananda Sagar University"
        p_f.font.name = "Calibri"
        p_f.font.size = Pt(11)
        p_f.font.bold = True
        p_f.font.color.rgb = SLATE

        # Footer right slide count
        tx_r = slide.shapes.add_textbox(Inches(10.5), Inches(6.98), Inches(2.0), Inches(0.45))
        tf_r = tx_r.text_frame
        p_r = tf_r.paragraphs[0]
        p_r.text = f"{slide_num_str} of 12"
        p_r.alignment = PP_ALIGN.RIGHT
        p_r.font.name = "Calibri"
        p_r.font.size = Pt(11)
        p_r.font.bold = True
        p_r.font.color.rgb = DARK_TEAL

    def create_card(slide, left, top, width, height, title, items):
        # Card container
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = BORDER_CLR
        card.line.width = Pt(1.2)

        # Card header ribbon
        ribbon = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left + 0.15), Inches(top + 0.15), Inches(width - 0.3), Inches(0.42))
        ribbon.fill.solid()
        ribbon.fill.fore_color.rgb = RGBColor(240, 253, 250)
        ribbon.line.color.rgb = RGBColor(153, 246, 228)
        ribbon.line.width = Pt(0.8)

        tx_h = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.15), Inches(width - 0.4), Inches(0.42))
        p_h = tx_h.text_frame.paragraphs[0]
        p_h.text = title
        p_h.font.name = "Calibri"
        p_h.font.size = Pt(13)
        p_h.font.bold = True
        p_h.font.color.rgb = DARK_TEAL
        p_h.vertical_anchor = MSO_ANCHOR.MIDDLE

        # Card content
        tx_c = slide.shapes.add_textbox(Inches(left + 0.25), Inches(top + 0.65), Inches(width - 0.5), Inches(height - 0.75))
        tf_c = tx_c.text_frame
        tf_c.word_wrap = True

        for idx, (label, desc) in enumerate(items):
            p = tf_c.add_paragraph() if idx > 0 else tf_c.paragraphs[0]
            p.space_after = Pt(6)
            run_lbl = p.add_run()
            run_lbl.text = f"• {label}: " if label else "• "
            run_lbl.font.name = "Calibri"
            run_lbl.font.bold = True
            run_lbl.font.size = Pt(11)
            run_lbl.font.color.rgb = NAVY

            run_desc = p.add_run()
            run_desc.text = desc
            run_desc.font.name = "Calibri"
            run_desc.font.bold = False
            run_desc.font.size = Pt(10.5)
            run_desc.font.color.rgb = SLATE

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY
    bg1.line.fill.background()

    # Top institutional header
    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(0.5), Inches(11.333), Inches(0.8))
    tf1 = t_box.text_frame
    p1 = tf1.paragraphs[0]
    p1.text = "DAYANANDA SAGAR UNIVERSITY"
    p1.alignment = PP_ALIGN.CENTER
    p1.font.name = "Calibri"
    p1.font.size = Pt(22)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(254, 240, 138)

    p2 = tf1.add_paragraph()
    p2.text = "SCHOOL OF ENGINEERING • DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING"
    p2.alignment = PP_ALIGN.CENTER
    p2.font.name = "Calibri"
    p2.font.size = Pt(13)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(203, 213, 225)

    # Accent divider
    div1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(3.0), Inches(1.5), Inches(7.333), Inches(0.04))
    div1.fill.solid()
    div1.fill.fore_color.rgb = TEAL
    div1.line.fill.background()

    # Title Card
    tcard = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(1.75), Inches(10.933), Inches(2.3))
    tcard.fill.solid()
    tcard.fill.fore_color.rgb = RGBColor(30, 41, 59)
    tcard.line.color.rgb = TEAL
    tcard.line.width = Pt(1.5)

    t_box2 = s1.shapes.add_textbox(Inches(1.5), Inches(1.9), Inches(10.333), Inches(2.0))
    tf2 = t_box2.text_frame
    tf2.word_wrap = True
    p_badge = tf2.paragraphs[0]
    p_badge.text = "MAJOR PROJECT PHASE-I (REVIEW 1)"
    p_badge.alignment = PP_ALIGN.CENTER
    p_badge.font.name = "Calibri"
    p_badge.font.size = Pt(13)
    p_badge.font.bold = True
    p_badge.font.color.rgb = TEAL

    p_title = tf2.add_paragraph()
    p_title.space_before = Pt(8)
    p_title.text = "An Artificial Intelligence Framework for Predictive Nutritional Risk Assessment and Early Malnutrition Stratification Using Machine Learning Based on Demography"
    p_title.alignment = PP_ALIGN.CENTER
    p_title.font.name = "Calibri"
    p_title.font.size = Pt(19)
    p_title.font.bold = True
    p_title.font.color.rgb = WHITE

    # Left Box: Team Members
    team_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(4.35), Inches(5.3), Inches(2.4))
    team_box.fill.solid()
    team_box.fill.fore_color.rgb = RGBColor(30, 41, 59)
    team_box.line.color.rgb = RGBColor(51, 65, 85)

    tx_team = s1.shapes.add_textbox(Inches(1.4), Inches(4.45), Inches(4.9), Inches(2.2))
    tf_team = tx_team.text_frame
    p_tm_lbl = tf_team.paragraphs[0]
    p_tm_lbl.text = "Presented By (Team 14):"
    p_tm_lbl.font.name = "Calibri"
    p_tm_lbl.font.size = Pt(13)
    p_tm_lbl.font.bold = True
    p_tm_lbl.font.color.rgb = TEAL

    members = [
        ("SAUGANDH K K", "ENG23CS0445"),
        ("SHARAN P NATH", "ENG23CS0452"),
        ("ULLAS S", "ENG23CS0213"),
        ("THARUN KUMAR P", "ENG23CS0211")
    ]
    for name, usn in members:
        p_m = tf_team.add_paragraph()
        p_m.space_before = Pt(3)
        r1 = p_m.add_run()
        r1.text = f"• {name} "
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = WHITE
        r2 = p_m.add_run()
        r2.text = f"({usn})"
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = RGBColor(148, 163, 184)

    # Right Box: Supervision & Academic Year
    sup_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.833), Inches(4.35), Inches(5.3), Inches(2.4))
    sup_box.fill.solid()
    sup_box.fill.fore_color.rgb = RGBColor(30, 41, 59)
    sup_box.line.color.rgb = RGBColor(51, 65, 85)

    tx_sup = s1.shapes.add_textbox(Inches(7.033), Inches(4.45), Inches(4.9), Inches(2.2))
    tf_sup = tx_sup.text_frame
    p_sup_lbl = tf_sup.paragraphs[0]
    p_sup_lbl.text = "Under the Supervision of:"
    p_sup_lbl.font.name = "Calibri"
    p_sup_lbl.font.size = Pt(13)
    p_sup_lbl.font.bold = True
    p_sup_lbl.font.color.rgb = TEAL

    p_sup_name = tf_sup.add_paragraph()
    p_sup_name.space_before = Pt(8)
    p_sup_name.text = "Prof. Dharmendra D P"
    p_sup_name.font.size = Pt(15)
    p_sup_name.font.bold = True
    p_sup_name.font.color.rgb = WHITE

    p_sup_des = tf_sup.add_paragraph()
    p_sup_des.text = "Assistant Professor, Dept. of CSE\nSchool of Engineering, DSU"
    p_sup_des.font.size = Pt(11)
    p_sup_des.font.color.rgb = RGBColor(203, 213, 225)

    p_ay = tf_sup.add_paragraph()
    p_ay.space_before = Pt(8)
    p_ay.text = "Academic Year: 2026–2027"
    p_ay.font.size = Pt(11.5)
    p_ay.font.bold = True
    p_ay.font.color.rgb = RGBColor(254, 240, 138)

    # =========================================================================
    # SLIDE 2: OVERVIEW
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header_footer(s2, "Overview of Major Project Phase-I", "2")

    sections = [
        ("01", "Abstract", "Executive summary of clinical malnutrition triage and ML approach"),
        ("02", "Project Objectives", "Purpose, relevance, boundary scope, and planned deliverables"),
        ("03", "Requirement Specification & Validation", "Target end-users, functional goals, technical stack, and safety constraints"),
        ("04", "Innovation & Potential Impact", "Core differentiators, creative problem solving, and commercialization scope"),
        ("05", "Literature Survey", "Comparative matrix of 5 recent landmark machine learning studies (2023–2026)"),
        ("06", "Research Gap", "Limitations of single-metric tools (BMI) and justification for multi-factor XAI"),
        ("07", "High-Level Design (Pipeline)", "Leakage-free preprocessing, feature engineering, and cross-validation setup"),
        ("08", "High-Level Design for Final System", "End-to-end architecture (Web, RBAC, ML inference, SQLite, and PDF export)"),
        ("09", "Implementation Highlights", "Working full-stack prototype verification, 139 automated tests, and benchmarks"),
        ("10", "List of Deliverables", "Phased breakdown of Review 0, Review 1, and Phase-II deliverables"),
        ("11", "References", "Formal IEEE/APA peer-reviewed scientific citations")
    ]

    # Two column grid for agenda
    for idx, (num, title, desc) in enumerate(sections):
        col = 0 if idx < 6 else 1
        row = idx if idx < 6 else idx - 6
        x = 0.8 + (col * 5.95)
        y = 1.35 + (row * 0.88)

        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(5.75), Inches(0.78))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = BORDER_CLR

        # Number pill
        pill = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x + 0.12), Inches(y + 0.12), Inches(0.55), Inches(0.54))
        pill.fill.solid()
        pill.fill.fore_color.rgb = DARK_TEAL
        pill.line.fill.background()
        p_num = pill.text_frame.paragraphs[0]
        p_num.text = num
        p_num.alignment = PP_ALIGN.CENTER
        p_num.font.name = "Calibri"
        p_num.font.bold = True
        p_num.font.size = Pt(13)
        p_num.font.color.rgb = WHITE

        tx = s2.shapes.add_textbox(Inches(x + 0.75), Inches(y + 0.08), Inches(4.9), Inches(0.62))
        tf = tx.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = "Calibri"
        p_t.font.size = Pt(11.5)
        p_t.font.bold = True
        p_t.font.color.rgb = NAVY

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = "Calibri"
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = SLATE

    # =========================================================================
    # SLIDE 3: ABSTRACT
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header_footer(s3, "Abstract", "3")

    create_card(s3, 0.8, 1.35, 11.733, 5.3, "Executive Summary & Clinical Contribution", [
        ("Clinical Background & Challenge", 
         "Adult malnutrition is a major global public health concern leading to prolonged morbidity, secondary infections, and increased healthcare expenditures. Conventional assessment tools (e.g., MUST, MNA) rely heavily on subjective interviews or invasive, costly blood biochemistry tests (such as serum albumin) that are unviable for high-throughput outpatient or rural screening."),
        ("Proposed AI Decision-Support System", 
         "This project designs and implements NutriRisk AI, an algorithmic clinical decision-support framework that evaluates 13 non-invasive demographic, anthropometric, dietary diversity, and lifestyle variables to classify adult individuals into Low, Moderate, or High Nutritional Risk."),
        ("Leakage-Free Preprocessing Pipeline", 
         "Body Mass Index (BMI = wt / (ht/100)^2) is dynamically engineered. Numerical variables undergo median imputation and standard scaling, while categorical features undergo mode imputation and one-hot encoding within a strict Scikit-Learn Pipeline to prevent data leakage."),
        ("Supervised ML Benchmark Results", 
         "Five algorithms were benchmarked via 5-fold cross-validation on an 80:20 stratified split of 6,000 adult records: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, and XGBoost. XGBoost achieved champion performance with 74.00% holdout accuracy, 0.7410 Macro-F1, and 0.8910 multi-class ROC-AUC."),
        ("Explainable AI (XAI) Transparency", 
         "To eliminate 'black-box' opacity in clinical triage, the framework integrates Explainable AI via TreeExplainer and localized feature attribution, giving clinicians transparent rationale into the specific dietary and biometric drivers behind every stratified prediction."),
        ("Software Engineering Delivery", 
         "The system is realized through an authenticated Flask 3.0 web application with Role-Based Access Control, SQLite WAL data persistence, batch patient screening, and automated ISO A4 clinical PDF report generation verified by 139 automated tests.")
    ])

    # =========================================================================
    # SLIDE 4: PROJECT OBJECTIVES
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header_footer(s4, "Project Objectives", "4")

    # 4 Cards in 2x2 grid
    create_card(s4, 0.8, 1.35, 5.75, 2.6, "Purpose & Objectives", [
        ("Multi-Factor Risk Modeling", "Construct an automated ML classifier using demographic, anthropometric, and dietary proxy variables to surpass single-indicator screening limitations."),
        ("Multi-Algorithm Benchmarking", "Evaluate 5 supervised classifiers using 5-fold cross-validation on an 80:20 split to identify the champion model based on Macro-F1 and ROC-AUC."),
        ("Transparent Decision Support", "Integrate localized Explainable AI (XAI) feature attribution to reveal the biometric and dietary factors influencing each risk output.")
    ])

    create_card(s4, 6.78, 1.35, 5.75, 2.6, "Problem & Relevance", [
        ("Epidemiological Relevance", "Malnutrition causes preventable health complications, poor recovery, and high hospital costs when left undetected during routine checkups."),
        ("Preventive Clinical Screening", "Enables healthcare providers to prioritize targeted nutritional counseling and proactive interventions before acute clinical deterioration occurs."),
        ("Community Screening Viability", "Replaces costly, invasive laboratory panels with non-invasive indicators accessible to primary health centers and community workers.")
    ])

    create_card(s4, 0.8, 4.15, 5.75, 2.6, "Scope Boundaries", [
        ("Target Age Scope", "Strictly calibrated for adult populations aged 18 to 90 years. Enforces strict input validation against pediatric screening."),
        ("Non-Diagnostic Decision Support", "Serves as an assistive screening triage aid rather than a definitive medical diagnostic device, explicitly guiding users to clinical consultation."),
        ("Data Modality", "Operates on structured tabular clinical and dietary features without requiring specialized biometric hardware or clinical laboratory draws.")
    ])

    create_card(s4, 6.78, 4.15, 5.75, 2.6, "Key Deliverables", [
        ("Serialized ML Model Pipeline", "Production-ready Scikit-Learn/XGBoost model bundle (`model.joblib`) with versioning metadata."),
        ("Web Application Interface", "Full-stack responsive interface with live BMI calculation, Under-18 modal protection, and cohort analytics."),
        ("Clinical Reporting Engine", "Automated vector ISO A4 PDF report generation providing personalized risk summaries and dietary recommendations."),
        ("Robust Persistence & Audit", "SQLite database with WAL mode, foreign key cascades, and clinician audit trails.")
    ])

    # =========================================================================
    # SLIDE 5: REQUIREMENT SPECIFICATION & VALIDATION
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header_footer(s5, "Requirement Specification & Validation", "5")

    create_card(s5, 0.8, 1.35, 5.75, 2.6, "Target Users", [
        ("Outpatient Clinicians & Dietitians", "Screen walk-in patients during routine health examinations to identify hidden undernutrition or dietary quality deficits."),
        ("Community Health Workers (ASHA)", "Conduct community-level nutritional triage using portable devices without needing laboratory equipment."),
        ("Hospital Administrators", "Audit longitudinal institutional screening volumes, track demographic patterns, and process high-throughput batch CSV uploads.")
    ])

    create_card(s5, 6.78, 1.35, 5.75, 2.6, "Expected Outcomes & Goals", [
        ("High Classification Robustness", "Achieve holdout Macro-F1 score $> 0.70$ across all 3 classes (Low, Moderate, High) despite natural class imbalance."),
        ("Sub-Second Inference Latency", "Execute feature pipeline transformation, XGBoost inference, and XAI attribution in $< 200\text{ ms}$."),
        ("100% Safety & Boundary Enforcement", "Automatically reject or intercept invalid ranges, missing mandatory parameters, and subjects $< 18$ years.")
    ])

    create_card(s5, 0.8, 4.15, 5.75, 2.6, "Tech Stack & Implementation Tools", [
        ("Python 3.12 Core Environment", "Python runtime with Scikit-Learn, XGBoost, and SHAP for machine learning and explainability."),
        ("Flask 3.0 & Bootstrap 5", "Modular Application Factory architecture with Blueprints, Jinja2 templating, and Chart.js telemetry."),
        ("Database & Security", "SQLite 3 with Write-Ahead Logging (WAL), Scrypt password hashing, and CSRF token protection."),
        ("Automated Quality Assurance", "Comprehensive 139-test regression suite covering routes, ML inference, and DB transactions.")
    ])

    create_card(s5, 6.78, 4.15, 5.75, 2.6, "Assumptions & Constraints", [
        ("Adult Demographic Calibrations", "Nutritional thresholds and BMI references are based on adult metabolic standards (age $\\ge 18$)."),
        ("Subject Integrity Assumption", "Assumes input parameters provided by the clinician or patient reflect reasonable self-reported accuracy."),
        ("Zero Data Leakage Constraint", "All imputations and feature transformations must be fit exclusively on training folds during cross-validation.")
    ])

    # =========================================================================
    # SLIDE 6: INNOVATION & POTENTIAL IMPACT
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header_footer(s6, "Innovation & Potential Impact", "6")

    create_card(s6, 0.8, 1.35, 5.75, 2.6, "Innovation & Creative Problem Solving", [
        ("Multi-Dimensional Feature Fusion", "Unifies anthropometric metrics (Height, Weight, BMI), dietary diversity (Food Groups 1–8, Meals/Day), and socioeconomic indicators."),
        ("Explainable AI Integration", "Translates mathematical model outputs into human-readable factor attributions, showing clinicians exactly which habits elevate patient risk."),
        ("Interactive Real-Time Intake", "Live client-side BMI categorization coupled with immediate server-side validation and ethical pediatric guardrails.")
    ])

    create_card(s6, 6.78, 1.35, 5.75, 2.6, "Differentiators from Existing Solutions", [
        ("Surpasses Single-Metric Blindspots", "Traditional BMI misses micronutrient deficiencies and sarcopenia; NutriRisk AI models non-linear risk interactions."),
        ("Eliminates Invasive Blood Draws", "Operates entirely on easily collectible clinical proxy indicators, drastically lowering screening costs and latency."),
        ("Continuous Probability Calibration", "Provides exact class probabilities rather than coarse, subjective checklist scores.")
    ])

    create_card(s6, 0.8, 4.15, 5.75, 2.6, "Potential Healthcare Impact", [
        ("Preventive Clinical Triage", "Identifies nutritional risk before physiological deterioration leads to severe medical complications or hospitalization."),
        ("Rural Healthcare Empowerment", "Brings specialized nutritional assessment capabilities to resource-constrained clinics lacking clinical dietitians."),
        ("Longitudinal Patient Tracking", "Enables health centers to monitor individual patient risk trajectories across follow-up consultations.")
    ])

    create_card(s6, 6.78, 4.15, 5.75, 2.6, "Scalability, Future Scope & Research", [
        ("High-Throughput Batch Processing", "Capable of screening hundreds of patient records simultaneously via batch CSV ingestion."),
        ("Cross-Platform Accessibility", "PWA capabilities and offline-first standalone app deployment for field workers with intermittent connectivity."),
        ("Academic Research Contribution", "Establishes a transparent, benchmarked open architecture for explainable machine learning in community nutrition.")
    ])

    # =========================================================================
    # SLIDE 7: LITERATURE SURVEY
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header_footer(s7, "Literature Survey", "7")

    # Table layout
    rows, cols = 6, 5
    left, top, width, height = Inches(0.8), Inches(1.35), Inches(11.733), Inches(5.3)
    table_shape = s7.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table

    # Column widths
    table.columns[0].width = Inches(2.6)
    table.columns[1].width = Inches(1.9)
    table.columns[2].width = Inches(2.3)
    table.columns[3].width = Inches(2.6)
    table.columns[4].width = Inches(2.333)

    headers = [
        "Author’s Name / Paper Title",
        "Journal / Conference & Year",
        "Technology / Design",
        "Results Shared by Author",
        "What We Infer"
    ]

    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.name = "Calibri"
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = WHITE

    lit_data = [
        ("Parchure et al.\n'Malnutrition risk assessment using ML-based screening'",
         "J. Human Nutrition & Dietetics (2024)",
         "Retrospective cohort (n=7,736);\nMUST-Plus tool embedded in hospital dietitian workflow.",
         "Identified 25.2% malnourished; improved early clinical detection & documentation rate.",
         "Automated screening enhances clinical triage, but inpatient tools rely heavily on retrospective EHR labs."),

        ("Chen, Pai, et al.\n'AI-assisted nutritional risk evaluation in critically ill'",
         "Asia Pacific J. Clin. Nutrition (2025)",
         "XGBoost, CatBoost, LightGBM vs. Logistic Regression (n=2,122 ICU patients); SHAP XAI.",
         "CatBoost achieved AUROC 0.926; age, low BMI, and albumin were primary predictors.",
         "Ensemble gradient boosting methods clearly outperform classical regression; XAI is vital for clinical trust."),

        ("Chen, Pan, et al.\n'ML for predicting malnutrition in thoracic surgery'",
         "Frontiers in Oncology (2026)",
         "Multi-center validation (n=1,407); 8 ML models; SHAP feature importance; web risk calculator.",
         "XGBoost AUC 0.845 (test) / 0.886 (external); ALB and age top predictors.",
         "Web-based risk calculators significantly accelerate clinical adoption; XGBoost generalizes well."),

        ("Di Martino et al.\n'Explainable AI for malnutrition prediction from m-Health'",
         "Smart Health (2023)",
         "Random Forest & Gradient Boosting on elderly clinical & sensor lifestyle data; SHAP.",
         "RF/GB achieved top classification; SHAP & permutation importance most consistent.",
         "Non-invasive lifestyle proxy features can effectively approximate risk without requiring continuous lab draws."),

        ("Islam et al.\n'Prediction of undernutrition using explainable ML'",
         "PLOS ONE (2024)",
         "Cross-sectional survey data (n=17,000+); Boruta feature selection, ANN, RF, XGBoost; SHAP.",
         "XGBoost best (AUC 0.802); household wealth, BMI, and parental education top predictors.",
         "Socioeconomic context and dietary diversity are crucial predictive signals for population malnutrition.")
    ]

    for r_idx, row_values in enumerate(lit_data):
        for c_idx, val in enumerate(row_values):
            cell = table.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if r_idx % 2 == 1 else WHITE
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = "Calibri"
            p.font.size = Pt(9.5)
            p.font.color.rgb = NAVY if c_idx == 0 else SLATE
            if c_idx == 0:
                p.font.bold = True

    # =========================================================================
    # SLIDE 8: RESEARCH GAP
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header_footer(s8, "Research Gap & Methodology Comparison", "8")

    # Table of comparison
    t_shape = s8.shapes.add_table(6, 3, Inches(0.8), Inches(1.35), Inches(11.733), Inches(2.7))
    t8 = t_shape.table
    t8.columns[0].width = Inches(2.7)
    t8.columns[1].width = Inches(4.5)
    t8.columns[2].width = Inches(4.533)

    t8_headers = ["Screening Method", "Key Advantages", "Observed Limitations & Gaps"]
    for c_idx, h_text in enumerate(t8_headers):
        cell = t8.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.name = "Calibri"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = WHITE

    comp_rows = [
        ("BMI-Only Assessment", "Rapid, non-invasive, universally calculated.", "Misses micronutrient deficiencies, normal-weight obesity, and acute muscle wasting."),
        ("Manual Tools (MNA / MUST)", "Standardized in hospital wards and geriatrics.", "Time-consuming (15–30 min), administrative burden, prone to subjective interview bias."),
        ("Laboratory Blood Panels", "High diagnostic precision (serum albumin, transferrin).", "Invasive, costly, requires lab infrastructure; unviable for rural and community triage."),
        ("Hospital EHR Deep Models", "High capacity on dense inpatient medical histories.", "Requires 40+ complex hospital laboratory features; opaque 'black-box' decisions."),
        ("NutriRisk AI (Proposed)", "Multi-factor, non-invasive, $<200\text{ ms}$, XAI transparency.", "Decision-support triage tool; necessitates clinical consultation for formal diagnosis.")
    ]

    for r_idx, (m_col, adv_col, lim_col) in enumerate(comp_rows):
        for c_idx, val in enumerate([m_col, adv_col, lim_col]):
            cell = t8.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(240, 253, 250) if r_idx == 4 else (RGBColor(248, 250, 252) if r_idx % 2 == 1 else WHITE)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = "Calibri"
            p.font.size = Pt(9.5)
            p.font.bold = True if (c_idx == 0 or r_idx == 4) else False
            p.font.color.rgb = DARK_TEAL if r_idx == 4 else (NAVY if c_idx == 0 else SLATE)

    # Research Gap Narrative Box
    create_card(s8, 0.8, 4.25, 11.733, 2.5, "Identified Research Gap & Proposed Project Solution", [
        ("The Primary Research Gap", 
         "Existing clinical screening tools either depend on single anthropometric metrics (like BMI) that overlook complex malnutrition phenotypes, or require costly laboratory panels inaccessible to primary clinics. Furthermore, existing algorithmic approaches rarely provide Explainable AI (XAI) feature importance to guide community health workers on physiological drivers."),
        ("How NutriRisk AI Bridges This Gap", 
         "Develops a lightweight, non-invasive machine learning framework fusing anthropometric, dietary diversity, and socioeconomic variables to deliver accurate risk stratification (Low, Moderate, High) with transparent localized feature attributions and immediate decision-support advice.")
    ])

    # =========================================================================
    # SLIDE 9: HIGH-LEVEL DESIGN (PIPELINE)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header_footer(s9, "High-Level Design: Data & ML Pipeline", "9")

    pipeline_steps = [
        ("Phase 1: Input Collection", "13 Non-Invasive Variables", [
            "Demographics: Age, Biological Sex",
            "Anthropometrics: Height (cm), Weight (kg)",
            "Dietary Diversity: Food Groups (1–8), Meals/Day",
            "Lifestyle: Physical Activity, Recent Acute Illness",
            "Socioeconomic: Income Tier, Education, Residence"
        ]),
        ("Phase 2: Feature Engineering", "BMI Derivation & Imputation", [
            "Derived: BMI = Weight (kg) / (Height (m))^2",
            "Under-18 Intercept: Strict Adult scope enforcement",
            "Numeric Imputation: Median (Leakage-Free)",
            "Categorical Imputation: Mode (Most Frequent)",
            "Transformation: StandardScaler & OneHotEncoder"
        ]),
        ("Phase 3: Model Benchmarking", "5 Supervised Classifiers", [
            "Stratified 80:20 Train/Test Partition",
            "5-Fold Cross-Validation on Training Split",
            "Algorithms: Logistic Reg., Decision Tree, RF, GB, XGBoost",
            "Champion: XGBoost (0.7410 CV Macro-F1, 0.8910 AUC)",
            "Serialization: Joblib artifact bundle with metadata"
        ]),
        ("Phase 4: Risk Stratification", "Decision Support & XAI", [
            "Continuous Multi-Class Probability Calibration",
            "Risk Tiers: Low Risk, Moderate Risk, High Risk",
            "Localized XAI: TreeExplainer Feature Attributions",
            "Dynamic Clinical Guidance & Next Steps",
            "Vector ISO A4 PDF Generation (ReportLab)"
        ])
    ]

    for idx, (title, sub, bullets) in enumerate(pipeline_steps):
        x = 0.8 + (idx * 2.98)
        card = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.35), Inches(2.8), Inches(5.3))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = BORDER_CLR
        card.line.width = Pt(1.2)

        # Step header
        sh = s9.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x + 0.1), Inches(1.45), Inches(2.6), Inches(0.7))
        sh.fill.solid()
        sh.fill.fore_color.rgb = NAVY if idx != 2 else DARK_TEAL
        sh.line.fill.background()

        p_sh = sh.text_frame.paragraphs[0]
        p_sh.text = title
        p_sh.alignment = PP_ALIGN.CENTER
        p_sh.font.name = "Calibri"
        p_sh.font.size = Pt(11)
        p_sh.font.bold = True
        p_sh.font.color.rgb = WHITE

        p_sub = sh.text_frame.add_paragraph()
        p_sub.text = sub
        p_sub.alignment = PP_ALIGN.CENTER
        p_sub.font.name = "Calibri"
        p_sub.font.size = Pt(9.5)
        p_sub.font.color.rgb = RGBColor(203, 213, 225) if idx != 2 else RGBColor(204, 251, 241)

        # Content
        tx = s9.shapes.add_textbox(Inches(x + 0.15), Inches(2.25), Inches(2.5), Inches(4.2))
        tf = tx.text_frame
        tf.word_wrap = True

        for b_idx, bullet in enumerate(bullets):
            p = tf.add_paragraph() if b_idx > 0 else tf.paragraphs[0]
            p.space_after = Pt(10)
            p.text = f"• {bullet}"
            p.font.name = "Calibri"
            p.font.size = Pt(10)
            p.font.color.rgb = SLATE

    # =========================================================================
    # SLIDE 10: HIGH-LEVEL DESIGN (FINAL SYSTEM ARCHITECTURE)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header_footer(s10, "High-Level Design for the Final System (Proposed)", "10")

    arch_layers = [
        ("Layer 1: User Presentation & Client Interfaces", [
            ("Clinical Assessment Intake", "Responsive HTML5/Bootstrap 5 form with live client-side BMI gauge and Under-18 modal."),
            ("Biometric Face ID Camera", "Webcam canvas integration for instant biometric clinician facial login."),
            ("Personal & Admin Dashboards", "Longitudinal risk charts, temporal screening activity, and multi-tenant user governance."),
            ("Progressive Web App (PWA)", "Service worker caching, web app manifest, and 1-click Windows desktop execution mode.")
        ]),
        ("Layer 2: Application Controller & Security (Flask Backend)", [
            ("Modular Blueprint Architecture", "Separation of concerns: Auth, Main, Assessment, Admin, and Analytics modules."),
            ("Role-Based Access Control (RBAC)", "Distinction between standard Clinicians and System Administrators."),
            ("Strict Request Validation", "Server-side boundary enforcement, CSRF token validation, and secure session management.")
        ]),
        ("Layer 3: Core ML Inference & Explainability Engine", [
            ("Pipeline Execution Engine", "Loads serialized `model.joblib` bundle with zero-leakage numeric and categorical encoders."),
            ("Multi-Class Probability Calibration", "Generates softmax risk probabilities for Low, Moderate, and High Risk tiers."),
            ("Explainable AI (XAI) Module", "Calculates tree-based feature attributions and localized factor decomposition for transparency.")
        ]),
        ("Layer 4: Data Persistence & Report Generation", [
            ("SQLite 3 Engine (WAL Mode)", "High-concurrency storage for users, patient assessment records, and model metadata audit trails."),
            ("Foreign Key Integrity", "Cascading deletions and relational integrity preserving longitudinal patient records."),
            ("ReportLab Vector PDF Engine", "Dynamic generation of clinical ISO A4 reports with XAI charts and medical disclaimers.")
        ])
    ]

    for idx, (layer_title, items) in enumerate(arch_layers):
        y = 1.35 + (idx * 1.35)
        create_card(s10, 0.8, y, 11.733, 1.25, layer_title, items)

    # =========================================================================
    # SLIDE 11: LIST OF DELIVERABLES
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header_footer(s11, "List of Deliverables (Phase-I & Phase-II)", "11")

    create_card(s11, 0.8, 1.35, 5.75, 5.3, "Phase-I Completed Deliverables (Review 0 & Review 1)", [
        ("Literature Review & Gap Synthesis", 
         "Systematic audit of 10 international peer-reviewed papers (2023–2026) and conventional screening instruments."),
        ("Standardized Clinical Cohort (N = 6,000)", 
         "Fully structured demographic and dietary dataset with comprehensive Exploratory Data Analysis (EDA) profiling."),
        ("Multi-Algorithm Benchmark Suite", 
         "Full training and evaluation pipeline for 5 classifiers with 5-fold cross-validation and hyperparameter optimization."),
        ("Champion Model Artifact (`model.joblib`)", 
         "Optimized XGBoost classifier achieving 74.00% accuracy, 0.7410 Macro-F1, and 0.8910 multi-class ROC-AUC."),
        ("Explainable AI (XAI) Attribution Module", 
         "TreeExplainer factor decomposition linking predictions directly to patient dietary and biometric habits."),
        ("Full-Stack Clinical Application", 
         "Working Flask 3.0 prototype with live BMI calculation, Under-18 modal, user auth, and audit telemetry."),
        ("Automated Quality Verification", 
         "139 passed automated unit and integration tests (100% pass rate) validating routes, security, and inference.")
    ])

    create_card(s11, 6.78, 1.35, 5.75, 5.3, "Phase-II Planned Deliverables (Review 2 & Final Viva)", [
        ("Empirical Clinical Survey Validation", 
         "Retraining and validation against real-world public health micro-data (e.g., NFHS-5 or NHANES cohorts)."),
        ("Advanced Batch Screening Enhancements", 
         "Enhanced multi-patient CSV ingestion with async processing for large regional epidemiological surveys."),
        ("Enhanced Longitudinal Trajectory Analytics", 
         "Advanced time-series charts visualizing patient recovery trajectories across sequential clinical consultations."),
        ("Edge & Offline Deployment Package", 
         "Lightweight containerized packaging for offline deployment on rural primary healthcare clinic tablets."),
        ("Final Major Project Thesis Dossier", 
         "Complete Capstone Project dissertation, Viva Voce presentation slide deck, and clinical user guide."),
        ("Academic Research Manuscript", 
         "Publication-ready manuscript prepared for submission to a peer-reviewed healthcare informatics journal.")
    ])

    # =========================================================================
    # SLIDE 12: REFERENCES
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header_footer(s12, "References", "12")

    refs = [
        "[1] Parchure, P., Besculides, M., Zhan, S., et al. (2024). Malnutrition risk assessment using a machine learning-based screening tool: A multicentre retrospective cohort. Journal of Human Nutrition and Dietetics, 37(3), 622–632. https://doi.org/10.1111/jhn.13286",
        "[2] Chen, C.-H., Pai, K.-C., Hsieh, H.-M., Chan, Y.-J., Hsu, H.-L., & Wang, C.-Y. (2025). Artificial intelligence assisted nutritional risk evaluation model for critically ill patients: Integration of explainable machine learning in intensive care nutrition. Asia Pacific Journal of Clinical Nutrition, 34(3), 343–352.",
        "[3] Chen, T., Pan, R., Liang, L., Xu, L., Yang, M., Deng, X., & Wang, P. (2026). Machine learning model for predicting malnutrition risk in lung cancer patients after thoracoscopic resection: A multi-center study. Frontiers in Oncology, 16, Article 1727595. https://doi.org/10.3389/fonc.2026.1727595",
        "[4] Di Martino, F., Delmastro, F., & Dolciotti, C. (2023). Explainable AI for malnutrition risk prediction from m-Health and clinical data. Smart Health, 30, Article 100429. https://doi.org/10.1016/j.smhl.2023.100429",
        "[5] Islam, M. M., Kibria, N. M. S. J., Kumar, S., Roy, D. C., & Karim, M. R. (2024). Prediction of undernutrition and identification of its influencing predictors among under-five children in Bangladesh using explainable machine learning algorithms. PLOS ONE, 19(12), e0315393. https://doi.org/10.1371/journal.pone.0315393",
        "[6] Rao, B., Rashid, M., Hasan, M. G., & Thunga, G. (2025). Machine learning in predicting child malnutrition: A meta-analysis of Demographic and Health Surveys data. International Journal of Environmental Research and Public Health, 22(3), Article 449. https://doi.org/10.3390/ijerph22030449",
        "[7] Jemil, H. W., Semayneh, S. W., Kassaw, A. B., Gashu, K. D., & Otekunrin, O. A. (2026). Predicting severe stunting and its determinants among under-five in Eastern African countries: A machine learning algorithms. PLOS ONE, 21(1), e0340221. https://doi.org/10.1371/journal.pone.0340221",
        "[8] Ahmed, E., & Rahman, A. (2026). Interpretable Bayesian machine learning models for predicting undernutrition among under-five children. Research Square [Preprint]. https://doi.org/10.21203/rs.3.rs-8871095/v1",
        "[9] Saleem, M. U., Aslam, M. U., Khatir, A. G., & Jiang, Q. (2025). Exploring risk factors and predictive modeling of child malnutrition in Pakistan using machine learning. American Journal of Human Biology, 37(9), e70124. https://doi.org/10.1002/ajhb.70124",
        "[10] Wicaksono, A., Prasetyo, D., Mar'atullatifah, Y., Iswavigra, D. U., Mahmudah, H., & Hapsari, A. (2025). Data analysis and explainable machine learning for stunting prediction. Journal of Artificial Intelligence and Legal Technology, 1(1), 35–44."
    ]

    ref_card = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(5.3))
    ref_card.fill.solid()
    ref_card.fill.fore_color.rgb = WHITE
    ref_card.line.color.rgb = BORDER_CLR
    ref_card.line.width = Pt(1.2)

    tx_r = s12.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(5.0))
    tf_r = tx_r.text_frame
    tf_r.word_wrap = True

    for i, ref in enumerate(refs):
        p = tf_r.add_paragraph() if i > 0 else tf_r.paragraphs[0]
        p.space_after = Pt(4)
        p.text = ref
        p.font.name = "Calibri"
        p.font.size = Pt(8.8)
        p.font.color.rgb = NAVY

    prs.save(output_path)
    print(f"Presentation successfully created at: {output_path}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "NutriRisk_AI_Phase_I_Review_1_Presentation.pptx"
    create_deck(out)
