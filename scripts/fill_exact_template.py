import copy
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

def create_presentation():
    template_path = r"C:/Users/ashok/.gemini/antigravity/brain/44422476-581e-429c-832a-13be1f058813/.user_uploaded/media_1792690280359_279513e2.pptx"
    prs = Presentation(template_path)
    print(f"Loaded template with {len(prs.slides)} slides.")

    # Color constants
    NAVY = RGBColor(15, 42, 74)
    TEXT_DARK = RGBColor(30, 41, 59)
    GRAY = RGBColor(71, 85, 105)
    TEAL = RGBColor(14, 116, 144)

    # ----------------------------------------------------
    # SLIDE 1: Title Slide
    # ----------------------------------------------------
    slide1 = prs.slides[0]
    for shape in slide1.shapes:
        if shape.name == "Rectangle 3" and "PROJECT TITLE" in (shape.text if shape.has_text_frame else ""):
            tf = shape.text_frame
            tf.clear()
            p0 = tf.paragraphs[0]
            p0.text = "An Artificial Intelligence Framework for Predictive Nutritional Risk Assessment and Early Malnutrition Stratification Using Machine Learning based on Demography"
            p0.font.bold = True
            p0.font.size = Pt(20)
            p0.font.color.rgb = NAVY
            p0.alignment = PP_ALIGN.CENTER
            
            p1 = tf.add_paragraph()
            p1.text = "Team No: 14"
            p1.font.bold = True
            p1.font.size = Pt(15)
            p1.font.color.rgb = TEAL
            p1.alignment = PP_ALIGN.CENTER

        elif shape.name == "TextBox 1" and shape.has_text_frame:
            tf = shape.text_frame
            tf.clear()
            p0 = tf.paragraphs[0]
            p0.text = "Presented By:"
            p0.font.bold = True
            p0.font.size = Pt(13)
            p0.font.color.rgb = NAVY

            members = [
                "SAUGANDH K K (ENG23CS0445)",
                "SHARAN P NATH (ENG23CS0452)",
                "ULLAS S (ENG23CS0213)",
                "THARUN KUMAR P (ENG23CS0211)"
            ]
            for m in members:
                p = tf.add_paragraph()
                p.text = m
                p.font.size = Pt(11)
                p.font.color.rgb = TEXT_DARK

        elif shape.name == "TextBox 5" and "Under the Supervision" in (shape.text if shape.has_text_frame else ""):
            tf = shape.text_frame
            tf.clear()
            p0 = tf.paragraphs[0]
            p0.text = "Under the Supervision Of:"
            p0.font.bold = True
            p0.font.size = Pt(13)
            p0.font.color.rgb = NAVY

            p1 = tf.add_paragraph()
            p1.text = "Prof. Dharmendra D P"
            p1.font.bold = True
            p1.font.size = Pt(12)
            p1.font.color.rgb = TEXT_DARK

            p2 = tf.add_paragraph()
            p2.text = "Assistant Professor, Dept. of CSE"
            p2.font.size = Pt(10)
            p2.font.color.rgb = GRAY

    # ----------------------------------------------------
    # SLIDE 2: Overview (Verify / refine if needed)
    # ----------------------------------------------------
    # Slide 2 is already standard agenda; keep it crisp.

    # ----------------------------------------------------
    # SLIDE 3: Abstract
    # ----------------------------------------------------
    slide3 = prs.slides[2]
    for shape in slide3.shapes:
        if shape.name == "Content Placeholder 2" and shape.has_text_frame:
            shape.left = Inches(1.0)
            shape.top = Inches(1.5)
            shape.width = Inches(8.0)
            shape.height = Inches(4.8)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.clear()

            points = [
                ("Clinical Motivation & Background",
                 "Adult malnutrition remains a widespread yet severely under-diagnosed public health challenge leading to elevated infection risks, delayed post-surgical recovery, longer hospital stays, and increased healthcare expenditure. Traditional clinical assessments depend heavily on manual, single-parameter methods (such as BMI alone) or invasive blood tests that often detect malnutrition only after critical physiological deterioration."),
                
                ("Proposed Solution (NutriRisk AI)",
                 "This project presents NutriRisk AI, an automated clinical decision-support framework that non-invasively stratifies individuals into Low, Moderate, or High malnutrition risk categories using 13 easily acquirable demographic, anthropometric, and dietary indicators without requiring invasive biochemical assays."),
                
                ("Dataset & Methodology",
                 "The system is trained and benchmarked on a clinical adult cohort of N = 6,000 individuals (aged 18-90 years). Preprocessing enforces zero data leakage, SMOTE class balancing, and 5-fold cross-validation across five machine learning algorithms: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, and XGBoost."),
                
                ("Performance & Benchmark Results",
                 "Extreme Gradient Boosting (XGBoost) emerged as the champion model, achieving 74.00% accuracy, 0.7410 Macro-F1 score, and 0.8910 multi-class ROC-AUC, demonstrating superior capability in capturing non-linear feature interactions."),
                
                ("Explainability & System Delivery",
                 "Integrated SHAP (Shapley Additive exPlanations) provides both global feature importance and patient-specific risk factor attribution. The end-to-end framework is fully operational with a responsive web interface, SQLite persistence, and verified by 139 passing automated test cases.")
            ]

            for i, (head, body) in enumerate(points):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = f"{head}: "
                p.font.bold = True
                p.font.size = Pt(11)
                p.font.color.rgb = NAVY
                p.space_after = Pt(6)

                run = p.add_run()
                run.text = body
                run.font.bold = False
                run.font.size = Pt(10.5)
                run.font.color.rgb = TEXT_DARK

    # ----------------------------------------------------
    # SLIDE 4: Project Objectives
    # ----------------------------------------------------
    slide4 = prs.slides[3]
    for shape in slide4.shapes:
        if shape.name == "Rectangle 8" and shape.has_text_frame:
            shape.left = Inches(1.0)
            shape.top = Inches(1.4)
            shape.width = Inches(8.0)
            shape.height = Inches(4.8)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.clear()

            obj_data = [
                ("Purpose and Objectives", [
                    "Develop an intelligent, non-invasive risk assessment tool for early malnutrition detection.",
                    "Benchmark five machine learning algorithms to achieve robust multi-class stratification (Low, Moderate, High).",
                    "Integrate Explainable AI (SHAP) to provide clinicians with transparent feature attributions behind every prediction."
                ]),
                ("Problem and Relevance", [
                    "Malnutrition is frequently missed during routine clinical checkups due to reliance on crude BMI cut-offs.",
                    "Existing laboratory-based nutritional evaluations are invasive, expensive, and unavailable in resource-limited settings.",
                    "Early, automated stratification enables proactive dietary intervention before adverse clinical complications occur."
                ]),
                ("Scope Boundaries", [
                    "Target Population: Adult cohort aged 18 to 90 years (pediatric cases are excluded from current calibration).",
                    "Feature Scope: 13 non-invasive clinical, demographic, dietary diversity, and anthropometric inputs.",
                    "Clinical Role: Acts strictly as a triage and screening decision-support aid, complementing healthcare practitioners."
                ]),
                ("Key Deliverables", [
                    "Leakage-free preprocessing and feature engineering pipeline with balanced multi-class distribution.",
                    "Trained and serialized champion XGBoost model bundle (model.joblib) with full audit logging.",
                    "Functional full-stack clinical decision-support web application with patient record persistence and PDF reports."
                ])
            ]

            for s_idx, (section, bullets) in enumerate(obj_data):
                p_head = tf.paragraphs[0] if s_idx == 0 else tf.add_paragraph()
                p_head.text = f"{section}:"
                p_head.font.bold = True
                p_head.font.size = Pt(12)
                p_head.font.color.rgb = NAVY
                p_head.space_after = Pt(2)
                if s_idx > 0:
                    p_head.space_before = Pt(6)

                for b in bullets:
                    p_b = tf.add_paragraph()
                    p_b.text = f"  -  {b}"
                    p_b.font.size = Pt(10)
                    p_b.font.color.rgb = TEXT_DARK
                    p_b.space_after = Pt(2)

    # ----------------------------------------------------
    # SLIDE 5: Requirement Specification & Validation
    # ----------------------------------------------------
    slide5 = prs.slides[4]
    for shape in slide5.shapes:
        if shape.name == "Content Placeholder 2" and shape.has_text_frame:
            shape.text_frame.clear()
        elif shape.name == "Rectangle 8" and shape.has_text_frame:
            shape.left = Inches(1.0)
            shape.top = Inches(1.3)
            shape.width = Inches(8.0)
            shape.height = Inches(4.9)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.clear()

            req_data = [
                ("Target Users", [
                    "Outpatient Clinicians & Dietitians: For rapid, objective nutritional risk screening during routine consultations.",
                    "Community Health Workers & Public Health Screeners: For scalable health camps and non-invasive field triage."
                ]),
                ("Expected Outcomes & Goals", [
                    "Achieve robust classification performance across all 3 risk tiers with Macro-F1 > 0.70 and ROC-AUC > 0.85.",
                    "Sub-50ms inference latency per patient for real-time, seamless integration at point-of-care.",
                    "Provide transparent clinical interpretability with local and global SHAP feature importance visualizations."
                ]),
                ("Tech Stack & Tools", [
                    "Core ML & Analytics: Python 3.12, Scikit-learn 1.4+, XGBoost 2.0+, SHAP 0.44+, Imbalanced-learn (SMOTE).",
                    "Application Framework: Flask 3.0, SQLite 3 (WAL mode for concurrent writes), ReportLab (PDF generation).",
                    "Frontend & Verification: HTML5/CSS3, Bootstrap 5, Pytest (139 passing automated unit and integration tests)."
                ]),
                ("Assumptions & Constraints", [
                    "Population Scope: Calibrated strictly for adults (18-90 years); pediatric physiology requires distinct baselines.",
                    "Non-Invasive Modality: Relies exclusively on non-invasive anthropometric, demographic, and dietary inputs."
                ])
            ]

            for s_idx, (section, bullets) in enumerate(req_data):
                p_head = tf.paragraphs[0] if s_idx == 0 else tf.add_paragraph()
                p_head.text = f"{section}:"
                p_head.font.bold = True
                p_head.font.size = Pt(12)
                p_head.font.color.rgb = NAVY
                p_head.space_after = Pt(2)
                if s_idx > 0:
                    p_head.space_before = Pt(6)

                for b in bullets:
                    p_b = tf.add_paragraph()
                    p_b.text = f"  -  {b}"
                    p_b.font.size = Pt(10)
                    p_b.font.color.rgb = TEXT_DARK
                    p_b.space_after = Pt(2)

    # ----------------------------------------------------
    # SLIDE 6: Innovation & Potential Impact
    # ZERO MENTIONS OF UN SDG 2 (Zero Hunger) OR SDGs!
    # ----------------------------------------------------
    slide6 = prs.slides[5]
    for shape in slide6.shapes:
        if shape.name == "Content Placeholder 2" and shape.has_text_frame:
            shape.text_frame.clear()
        elif shape.name == "Rectangle 8" and shape.has_text_frame:
            shape.left = Inches(0.8)
            shape.top = Inches(1.3)
            shape.width = Inches(8.4)
            shape.height = Inches(4.9)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.clear()

            innov_data = [
                ("Innovation Aspects", "Integrates multi-dimensional lifestyle, dietary diversity, and demographic indicators rather than isolated BMI measurements."),
                ("Differentiators from Existing Solutions", "Overcomes single-metric blindspots (e.g. sarcopenic obesity and micronutrient malnutrition) with non-invasive ML triage."),
                ("Creative Problem Solving Techniques", "Employs SMOTE resampling to eliminate class imbalance bias and TreeSHAP for patient-specific clinical explainability."),
                ("Potential Impact", "Enables rapid early detection, preventing costly hospital readmissions and irreversible physiological deterioration."),
                ("Public Health & Clinical Alignment", "Supports proactive community health screening, preventive care delivery, and timely nutritional counseling for vulnerable populations."),
                ("Scalability and Future Scope", "Modular microservice-ready backend architecture ready for high-throughput hospital batch screening and EHR/FHIR interoperability."),
                ("Commercialization & Deployment", "Lightweight, cloud-portable and edge-friendly design suitable for outpatient clinics, diagnostic centers, and wellness platforms."),
                ("Academic & Research Contribution", "Presents an empirical comparative benchmark of 5 supervised ML models on N = 6,000 adult profiles with validated XAI interpretability.")
            ]

            for s_idx, (section, text) in enumerate(innov_data):
                p = tf.paragraphs[0] if s_idx == 0 else tf.add_paragraph()
                p.text = f"{section}: "
                p.font.bold = True
                p.font.size = Pt(10.5)
                p.font.color.rgb = NAVY
                p.space_after = Pt(3)

                run = p.add_run()
                run.text = text
                run.font.bold = False
                run.font.size = Pt(10)
                run.font.color.rgb = TEXT_DARK

    # ----------------------------------------------------
    # SLIDE 7: Literature Survey
    # ----------------------------------------------------
    slide7 = prs.slides[6]
    table_shape = None
    for shape in slide7.shapes:
        if shape.has_table:
            table_shape = shape
            break

    if table_shape:
        table_shape.left = Inches(0.6)
        table_shape.top = Inches(1.3)
        table_shape.width = Inches(8.8)
        table_shape.height = Inches(4.8)
        
        tbl = table_shape.table._tbl
        # Expand rows to 6 (1 header + 5 papers)
        while len(table_shape.table.rows) < 6:
            new_row = copy.deepcopy(tbl.tr_lst[1])
            tbl.append(new_row)

        lit_data = [
            ("Rao, B., Rashid, M., et al. (2025)\nMachine Learning in Predicting Child Malnutrition: A Meta-Analysis",
             "Int. J. Environ. Res. Public Health (2025)",
             "Meta-analysis of 11 ML studies on DHS data; PROBAST bias assessment; pooled via Review Manager 5.4",
             "Pooled accuracy: 68.9% stunting, 84.4% wasting, 73.6% underweight across pooled cohorts",
             "ML substantially outperforms single-metric screening; highlighted necessity of rigorous, leak-free evaluation pipelines."),
            
            ("Jemil, H. W., Semayneh, S. W., et al. (2026)\nPredicting severe stunting and its determinants in East Africa",
             "PLOS ONE (2026)",
             "Cross-sectional DHS data (N = 76,019 children); ML algorithms + SHAP + Association Rule Mining",
             "Identified maternal education, wealth index, and child age as primary determinants of malnutrition",
             "Model interpretability (XAI) via SHAP is essential for clinical trust and actionable decision support."),
            
            ("Ahmed, E., & Rahman, A. (2026)\nInterpretable Bayesian Machine Learning Models for Undernutrition",
             "Research Square [Preprint] (2026)",
             "BDHS 2022 survey data (N = 4,260); Logistic Regression, Bayesian Spike-and-Slab, BART; 10-fold CV",
             "Bayesian Spike-and-Slab achieved top AUC (0.63); maternal BMI and child age were key risk factors",
             "Linear/Bayesian models showed modest AUC; complex multi-factorial data benefits from non-linear tree ensembles."),
            
            ("Saleem, M. U., Aslam, M. U., et al. (2025)\nPredictive Modeling of Child Malnutrition using ML",
             "American J. Human Biology (2025)",
             "PDHS 2017-18 dataset; Logistic Regression for risk factors; RF, SVM, Naive Bayes, AdaBoost; 10-fold CV",
             "Random Forest was the top-performing classifier; parental education and wealth index were critical",
             "Ensemble learning architectures consistently outperform standalone linear classifiers on demographic health data."),
            
            ("Wicaksono, A., Prasetyo, D., et al. (2025)\nExplainable Machine Learning for Stunting Prediction",
             "J. AI & Legal Technology (2025)",
             "Cohort (N = 40,071); LR, SVM, MLP, KNN, DT, RF, XGBoost, CNN; global & local SHAP explanations",
             "XGBoost achieved champion performance (97.57% accuracy); height and age were most influential",
             "Gradient boosting (XGBoost) combined with SHAP provides the optimal balance of predictive power and clinical transparency.")
        ]

        # Format header row
        headers = ["Author's Name / Paper Title", "Conference / Journal (Year)", "Technology / Design", "Results Shared by Author", "Inference for NutriRisk AI"]
        for c_idx, title in enumerate(headers):
            cell = table_shape.table.cell(0, c_idx)
            cell.text = title
            for p in cell.text_frame.paragraphs:
                p.font.bold = True
                p.font.size = Pt(9.5)
                p.font.color.rgb = RGBColor(255, 255, 255)
                p.alignment = PP_ALIGN.CENTER
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY

        # Format data rows
        for r_idx, row_data in enumerate(lit_data, start=1):
            for c_idx, val in enumerate(row_data):
                cell = table_shape.table.cell(r_idx, c_idx)
                cell.text = val
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(8.5)
                    p.font.color.rgb = TEXT_DARK
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if r_idx % 2 == 1 else RGBColor(255, 255, 255)

    # ----------------------------------------------------
    # SLIDE 8: High-Level Design (Pipeline)
    # ----------------------------------------------------
    slide8 = prs.slides[7]
    for shape in slide8.shapes:
        if shape.name == "Content Placeholder 1" and shape.has_text_frame:
            shape.left = Inches(1.0)
            shape.top = Inches(1.4)
            shape.width = Inches(8.0)
            shape.height = Inches(4.8)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.clear()

            phases = [
                ("Phase 1: Multi-Source Data Intake & Ingestion", [
                    "Captures 13 clinically relevant non-invasive attributes from N = 6,000 adult profiles.",
                    "Input parameters encompass demographics (age, sex), anthropometrics (height, weight), dietary patterns, and clinical indicators.",
                    "Strict boundary validation enforces adult target cohort constraints (18-90 years)."
                ]),
                ("Phase 2: Leakage-Free Preprocessing & Feature Engineering", [
                    "Strict partition-first architecture: Imputation, scaling, and encodings are fit exclusively on training data.",
                    "Derived physiological features: Body Mass Index (BMI = Weight / Height^2) and Dietary Diversity Index.",
                    "Categorical variables processed via robust one-hot encoding with schema preservation."
                ]),
                ("Phase 3: Class Imbalance Remediation via SMOTE", [
                    "Synthetic Minority Over-sampling Technique (SMOTE) applied strictly to training folds.",
                    "Balances representation across Low, Moderate, and High nutritional risk categories, preventing majority class bias."
                ]),
                ("Phase 4: Multi-Model Benchmark & Cross-Validation", [
                    "Stratified 5-Fold Cross-Validation across 5 supervised algorithms: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, and XGBoost.",
                    "Evaluation across multi-class accuracy, precision, recall, Macro-F1, and ROC-AUC."
                ]),
                ("Phase 5: Champion Model Selection & Serialization", [
                    "XGBoost selected as champion: 74.00% accuracy, 0.7410 Macro-F1, and 0.8910 multi-class ROC-AUC.",
                    "Exported into versioned, production-ready pipeline bundle (model.joblib) with sub-50ms inference latency."
                ])
            ]

            for s_idx, (section, bullets) in enumerate(phases):
                p_head = tf.paragraphs[0] if s_idx == 0 else tf.add_paragraph()
                p_head.text = f"{section}:"
                p_head.font.bold = True
                p_head.font.size = Pt(11)
                p_head.font.color.rgb = NAVY
                p_head.space_after = Pt(2)
                if s_idx > 0:
                    p_head.space_before = Pt(5)

                for b in bullets:
                    p_b = tf.add_paragraph()
                    p_b.text = f"  -  {b}"
                    p_b.font.size = Pt(9.5)
                    p_b.font.color.rgb = TEXT_DARK
                    p_b.space_after = Pt(1)

    # ----------------------------------------------------
    # SLIDE 9: High-Level Design for Final System
    # ----------------------------------------------------
    slide9 = prs.slides[8]
    for shape in slide9.shapes:
        if shape.name == "Content Placeholder 1" and shape.has_text_frame:
            shape.left = Inches(1.0)
            shape.top = Inches(1.4)
            shape.width = Inches(8.0)
            shape.height = Inches(4.8)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.clear()

            layers = [
                ("Layer 1: Presentation & Clinical User Interface", [
                    "Responsive Web Portal (Bootstrap 5, Jinja2) and mobile-friendly assessment intake form.",
                    "Real-time client-side BMI calculator and dynamic input bounds validation.",
                    "Interactive Clinical Dashboard displaying risk badges (Low/Moderate/High), probability distributions, and dietary advice."
                ]),
                ("Layer 2: Application Controller & Security (Flask Backend)", [
                    "Modular Blueprint Architecture: Auth, Main, Assessment Intake, Admin, and Analytics modules.",
                    "Security Framework: Role-Based Access Control (Clinician, Admin), CSRF protection, input sanitization, and session timeouts.",
                    "RESTful API service providing high-throughput batch and single-patient screening endpoints."
                ]),
                ("Layer 3: Core ML Inference & Explainability Engine", [
                    "High-performance inference engine loading serialized XGBoost pipeline with < 50ms response time.",
                    "Explainable AI (XAI) Subsystem: SHAP TreeExplainer generates local feature attribution waterfall/force plots for every patient.",
                    "Clinical Safety Guardrails: Deterministic safety rules override predictions under extreme physiological conditions."
                ]),
                ("Layer 4: Data Persistence & Report Generation", [
                    "SQLite 3 transactional database running in Write-Ahead Logging (WAL) mode for concurrency and zero-locking bottlenecks.",
                    "Automated Clinical Report Generator (ReportLab) compiling patient summaries, SHAP insights, and diet recommendations into PDF.",
                    "Comprehensive audit logging capturing all prediction events, timestamps, and model version identifiers."
                ])
            ]

            for s_idx, (section, bullets) in enumerate(layers):
                p_head = tf.paragraphs[0] if s_idx == 0 else tf.add_paragraph()
                p_head.text = f"{section}:"
                p_head.font.bold = True
                p_head.font.size = Pt(11.5)
                p_head.font.color.rgb = NAVY
                p_head.space_after = Pt(2)
                if s_idx > 0:
                    p_head.space_before = Pt(6)

                for b in bullets:
                    p_b = tf.add_paragraph()
                    p_b.text = f"  -  {b}"
                    p_b.font.size = Pt(9.5)
                    p_b.font.color.rgb = TEXT_DARK
                    p_b.space_after = Pt(2)

    # ----------------------------------------------------
    # SLIDE 10: List of Deliverables
    # ----------------------------------------------------
    slide10 = prs.slides[9]
    # Check if a text box exists or create one
    deliv_box = None
    for shape in slide10.shapes:
        if shape.name not in ["Title 1", "Date Placeholder 3", "Footer Placeholder 4", "Slide Number Placeholder 1"]:
            if shape.has_text_frame:
                deliv_box = shape
                break

    if not deliv_box:
        deliv_box = slide10.shapes.add_textbox(Inches(1.0), Inches(1.4), Inches(8.0), Inches(4.8))

    deliv_box.left = Inches(1.0)
    deliv_box.top = Inches(1.4)
    deliv_box.width = Inches(8.0)
    deliv_box.height = Inches(4.8)
    tf = deliv_box.text_frame
    tf.word_wrap = True
    tf.clear()

    deliv_data = [
        ("Phase-I Completed Deliverables (Review 0 & Review 1 Milestones)", [
            "Comprehensive Literature Survey: Systematic review and comparison of 10 international peer-reviewed papers (2023-2026).",
            "Clinical Problem Definition & Requirement Specification: Defined clinical boundaries and adult target cohort (18-90 years).",
            "Leakage-Free Preprocessing & Feature Engineering Pipeline: Automated data pipeline for N = 6,000 adult profiles.",
            "Multi-Model Benchmarking Suite: 5 supervised classifiers evaluated; XGBoost selected as champion (74% accuracy, 0.7410 Macro-F1).",
            "Working Full-Stack Prototype: Interactive web interface with real-time risk classification and persistent SQLite database.",
            "Quality Assurance Suite: 139 passing automated unit, integration, and security test cases."
        ]),
        ("Phase-II Planned Deliverables (Review 2 & Final Viva Milestones)", [
            "Enhanced Explainable AI (XAI) Visualizer: Interactive patient-facing SHAP waterfall graphs embedded into the clinician UI.",
            "Automated PDF Clinical Report Generation: Comprehensive downloadable patient summary and tailored nutrition plans.",
            "Offline Community Health Screening Mode: Progressive Web App (PWA) / offline mobile deployment for rural health camps.",
            "Real-World Dataset Validation: External validation against public health demographic datasets for broader generalization.",
            "Final Capstone Dissertation, IEEE Conference Paper Submission, and Final Project Defense."
        ])
    ]

    for s_idx, (section, bullets) in enumerate(deliv_data):
        p_head = tf.paragraphs[0] if s_idx == 0 else tf.add_paragraph()
        p_head.text = f"{section}:"
        p_head.font.bold = True
        p_head.font.size = Pt(12)
        p_head.font.color.rgb = NAVY
        p_head.space_after = Pt(3)
        if s_idx > 0:
            p_head.space_before = Pt(8)

        for b in bullets:
            p_b = tf.add_paragraph()
            p_b.text = f"  -  {b}"
            p_b.font.size = Pt(9.5)
            p_b.font.color.rgb = TEXT_DARK
            p_b.space_after = Pt(2)

    # ----------------------------------------------------
    # SLIDE 11: References
    # ----------------------------------------------------
    slide11 = prs.slides[10]
    for shape in slide11.shapes:
        if shape.name == "Content Placeholder 2" and shape.has_text_frame:
            shape.left = Inches(0.8)
            shape.top = Inches(1.3)
            shape.width = Inches(8.4)
            shape.height = Inches(4.9)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.clear()

            citations = [
                "[1] Parchure, P., Besculides, M., Zhan, S., et al. (2024). Malnutrition risk assessment using a machine learning-based screening tool: A multicentre retrospective cohort. Journal of Human Nutrition and Dietetics, 37(3), 622-632.",
                "[2] Chen, C.-H., Pai, K.-C., Hsieh, H.-M., et al. (2025). Artificial intelligence assisted nutritional risk evaluation model for critically ill patients: Integration of explainable machine learning in intensive care nutrition. Asia Pacific Journal of Clinical Nutrition, 34(3), 343-352.",
                "[3] Chen, T., Pan, R., Liang, L., et al. (2026). Machine learning model for predicting malnutrition risk in lung cancer patients after thoracoscopic resection: A multi-center study. Frontiers in Oncology, 16, Article 1727595.",
                "[4] Di Martino, F., Delmastro, F., & Dolciotti, C. (2023). Explainable AI for malnutrition risk prediction from m-Health and clinical data. Smart Health, 30, Article 100429.",
                "[5] Islam, M. M., Kibria, N. M. S. J., Kumar, S., et al. (2024). Prediction of undernutrition and identification of its influencing predictors among under-five children using explainable machine learning algorithms. PLOS ONE, 19(12), e0315393.",
                "[6] Rao, B., Rashid, M., Hasan, M. G., & Thunga, G. (2025). Machine learning in predicting child malnutrition: A meta-analysis of Demographic and Health Surveys data. International Journal of Environmental Research and Public Health, 22(3), Article 449.",
                "[7] Jemil, H. W., Semayneh, S. W., Kassaw, A. B., et al. (2026). Predicting severe stunting and its determinants among under-five in Eastern African countries: A machine learning approach. PLOS ONE, 21(1), e0340221.",
                "[8] Ahmed, E., & Rahman, A. (2026). Interpretable Bayesian machine learning models for predicting undernutrition among under-five children. Research Square [Preprint].",
                "[9] Saleem, M. U., Aslam, M. U., Khatir, A. G., & Jiang, Q. (2025). Exploring risk factors and predictive modeling of child malnutrition in Pakistan using machine learning. American Journal of Human Biology, 37(9), e70124.",
                "[10] Wicaksono, A., Prasetyo, D., Mar'atullatifah, Y., et al. (2025). Data analysis and explainable machine learning for stunting prediction. Journal of Artificial Intelligence and Legal Technology, 1(1), 35-44."
            ]

            for c_idx, cit in enumerate(citations):
                p = tf.paragraphs[0] if c_idx == 0 else tf.add_paragraph()
                p.text = cit
                p.font.size = Pt(8.5)
                p.font.color.rgb = TEXT_DARK
                p.space_after = Pt(3)

    # Save outputs
    out_dir1 = r"d:\MAJOR PROJECT"
    out_dir2 = r"C:\Users\ashok\.gemini\antigravity\brain\44422476-581e-429c-832a-13be1f058813"
    out_filename = "NutriRisk_AI_Phase_I_Review_1_Presentation.pptx"

    out_path1 = os.path.join(out_dir1, out_filename)
    out_path2 = os.path.join(out_dir2, out_filename)

    prs.save(out_path1)
    prs.save(out_path2)
    print(f"Successfully saved filled presentation to:\n  1. {out_path1}\n  2. {out_path2}")

if __name__ == "__main__":
    create_presentation()
