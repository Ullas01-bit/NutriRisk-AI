"""
Clinical PDF Report Generator for NutriRisk AI (Prompt 19).

Generates an audit-ready, publication-grade clinical assessment report on standard A4 paper using ReportLab.
Contains:
  1. NutriRisk AI institutional branding and header.
  2. Assessment identification (ID, Date & Timestamp, Assessor name, Subject identifier).
  3. Stratified Risk Classification, Model Confidence, and Body Mass Index (BMI).
  4. Complete demographic, nutritional, lifestyle, and socioeconomic inputs table.
  5. Multi-Class Posterior Probability Distribution (Low, Moderate, High Risk).
  6. Explainable AI (XAI) local factor attributions with direction and plain-language clinical summaries.
  7. Stratified general next-step guidance and recommended action protocol.
  8. Model architecture and artifact versioning metadata.
  9. Formal academic research and clinical decision-support disclaimer.
  10. Strict privacy: zero exposure of private authentication credentials or password hashes.
"""
import io
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

# Clinical Design System Palette
COLOR_TEAL_DARK = colors.HexColor("#0f766e")
COLOR_TEAL = colors.HexColor("#0d9488")
COLOR_TEAL_LIGHT = colors.HexColor("#ccfbf1")
COLOR_SLATE_DARK = colors.HexColor("#0f172a")
COLOR_SLATE_MUTED = colors.HexColor("#64748b")
COLOR_BG_LIGHT = colors.HexColor("#f8fafc")
COLOR_BORDER = colors.HexColor("#e2e8f0")

COLOR_LOW = colors.HexColor("#16a34a")       # Emerald
COLOR_MODERATE = colors.HexColor("#d97706")  # Amber
COLOR_HIGH = colors.HexColor("#dc2626")      # Red


def _draw_page_decorations(canvas, doc):
    """Draws running header and running footer on each page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(COLOR_SLATE_MUTED)

    # Top running header rule
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.setLineWidth(0.5)

    # Bottom running footer
    footer_y = 22
    canvas.line(doc.leftMargin, footer_y + 10, doc.pagesize[0] - doc.rightMargin, footer_y + 10)
    canvas.drawString(
        doc.leftMargin,
        footer_y,
        "NutriRisk AI &bull; Clinical Decision-Support System &bull; Confidential Assessment Report &bull; A4"
    )
    page_text = f"Page {canvas._pageNumber}"
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, footer_y, page_text)
    canvas.restoreState()


def generate_assessment_pdf(
    assessment_record: Dict[str, Any],
    inputs_dict: Dict[str, Any],
    advice_text: str,
    disclaimer_text: str,
    assessor_name: str = "Healthcare Clinician",
    model_name: str = "XGBoost Classifier"
) -> io.BytesIO:
    """
    Generates a professional A4 clinical assessment report in memory and returns a BytesIO buffer.
    Printable width on A4 with 0.45in margins is exactly 530 points.
    """
    buffer = io.BytesIO()
    # A4 dimensions: 595.27 x 841.89 points
    # Margins: 0.45 in (32.4 pt) left/right -> usable width = 530.47 pt
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=32.4,
        leftMargin=32.4,
        topMargin=28.0,
        bottomMargin=36.0
    )

    styles = getSampleStyleSheet()

    # Typography styles
    style_title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=COLOR_SLATE_DARK
    )
    style_subtitle = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=COLOR_SLATE_MUTED
    )
    style_h2 = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=COLOR_TEAL_DARK,
        spaceAfter=4
    )
    style_body = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=COLOR_SLATE_DARK
    )
    style_body_bold = ParagraphStyle(
        "BodyDarkBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=COLOR_SLATE_DARK
    )
    style_body_muted = ParagraphStyle(
        "BodyMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        textColor=COLOR_SLATE_MUTED
    )
    style_table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=COLOR_SLATE_DARK
    )
    style_table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )

    elements = []
    TOTAL_WIDTH = 530.0  # Exact printable width in points

    # 1. Header Banner: Institutional branding & metadata
    created_str = str(assessment_record.get("created", ""))
    date_display = created_str.replace("T", " ")[:19] if created_str else datetime.now().strftime("%Y-%m-%d %H:%M")
    model_version_str = str(assessment_record.get("model_version", "v1.0-xgboost"))

    header_data = [
        [
            Paragraph("<b>NutriRisk AI</b> &bull; Clinical Decision Support<br/>"
                      "<font size='8' color='#64748b'>Predictive Nutritional Risk Assessment &amp; Malnutrition Stratification</font>", style_title),
            Paragraph(f"<b>Assessment ID:</b> #{assessment_record.get('id', 'N/A')}<br/>"
                      f"<b>Date:</b> {date_display}<br/>"
                      f"<b>Conducted By:</b> {assessor_name}<br/>"
                      f"<b>Model Pipeline:</b> {model_name} ({model_version_str})", style_subtitle)
        ]
    ]
    header_table = Table(header_data, colWidths=[340.0, 190.0])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_TEAL, spaceBefore=6, spaceAfter=8))

    # 2. Risk Classification Banner & KPI Summary
    risk_label = str(assessment_record.get("risk", "Unknown")).upper()
    confidence = float(assessment_record.get("confidence", 0.0)) * 100
    risk_color = COLOR_LOW if "LOW" in risk_label else (COLOR_MODERATE if "MODERATE" in risk_label else COLOR_HIGH)

    bmi = float(inputs_dict.get("bmi", assessment_record.get("bmi", 0.0)))
    if bmi <= 0.0 and float(inputs_dict.get("height_cm", 0.0)) > 0:
        h_m = float(inputs_dict["height_cm"]) / 100.0
        w_kg = float(inputs_dict.get("weight_kg", 0.0))
        bmi = round(w_kg / (h_m ** 2), 2)

    bmi_category = (
        "Underweight (<18.5)" if bmi < 18.5 else
        ("Normal Range (18.5-24.9)" if bmi < 25.0 else
         ("Overweight (25.0-29.9)" if bmi < 30.0 else "Obese Range (>=30.0)"))
    )

    kpi_data = [
        [
            Paragraph(f"<b>STRATIFIED RISK TIER:</b><br/>"
                      f"<font size='13' color='{risk_color.hexval()}'><b>{risk_label}</b></font><br/>"
                      f"<font size='7.5' color='#64748b'>Triage Category</font>", style_body),
            Paragraph(f"<b>PREDICTION CONFIDENCE:</b><br/>"
                      f"<font size='13' color='{COLOR_TEAL_DARK.hexval()}'><b>{confidence:.1f}%</b></font><br/>"
                      f"<font size='7.5' color='#64748b'>Predicted Class Probability</font>", style_body),
            Paragraph(f"<b>BODY MASS INDEX (BMI):</b><br/>"
                      f"<font size='13'><b>{bmi:.2f} kg/m²</b></font><br/>"
                      f"<font size='7.5' color='#64748b'>{bmi_category}</font>", style_body)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[176.0, 176.0, 178.0])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 8))

    # 3. Patient Demographics & Nutritional Features
    elements.append(Paragraph("1. Patient Demographics &amp; Clinical Input Parameters", style_h2))

    subject_name = str(assessment_record.get("subject", "Self Assessment"))
    profile_data = [
        [
            Paragraph("<b>Subject / Patient ID:</b>", style_body), Paragraph(subject_name, style_body),
            Paragraph("<b>Age &bull; Biological Sex:</b>", style_body), Paragraph(f"{inputs_dict.get('age', '-')} yrs &bull; {inputs_dict.get('sex', '-')}", style_body),
        ],
        [
            Paragraph("<b>Stature &bull; Weight:</b>", style_body), Paragraph(f"{inputs_dict.get('height_cm', '-')} cm &bull; {inputs_dict.get('weight_kg', '-')} kg", style_body),
            Paragraph("<b>Dietary Diversity:</b>", style_body), Paragraph(f"{inputs_dict.get('food_groups', '-')} / 8 Food Groups Daily", style_body),
        ],
        [
            Paragraph("<b>Meal Frequency:</b>", style_body), Paragraph(f"{inputs_dict.get('meals_per_day', '-')} Meals / Day", style_body),
            Paragraph("<b>Physical Activity:</b>", style_body), Paragraph(str(inputs_dict.get("activity", "-")), style_body),
        ],
        [
            Paragraph("<b>Household Income:</b>", style_body), Paragraph(str(inputs_dict.get("income", "-")), style_body),
            Paragraph("<b>Recent Illness (30d):</b>", style_body), Paragraph(str(inputs_dict.get("recent_illness", "-")), style_body),
        ],
        [
            Paragraph("<b>Educational Level:</b>", style_body), Paragraph(str(inputs_dict.get("education", "-")), style_body),
            Paragraph("<b>Residence Setting:</b>", style_body), Paragraph(str(inputs_dict.get("residence", "-")), style_body),
        ]
    ]
    profile_table = Table(profile_data, colWidths=[125.0, 140.0, 125.0, 140.0])
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(profile_table)
    elements.append(Spacer(1, 8))

    # 4. Multi-Class Posterior Probability Distribution
    elements.append(Paragraph("2. Multi-Class Posterior Probability Distribution", style_h2))
    raw_probs = assessment_record.get("probs", "[]")
    if isinstance(raw_probs, str):
        try:
            probs = json.loads(raw_probs)
        except Exception:
            probs = [0.0, 0.0, 0.0]
    elif isinstance(raw_probs, list):
        probs = raw_probs
    else:
        probs = [0.0, 0.0, 0.0]

    from nutririsk.ml.features import LABELS

    prob_headers = [Paragraph(f"<b>{label}</b>", style_table_header) for label in LABELS]
    prob_values = []
    for i, label in enumerate(LABELS):
        p_val = (probs[i] * 100) if i < len(probs) else 0.0
        is_pred = (label.upper() in risk_label)
        color_val = "#0f766e" if is_pred else "#0f172a"
        prob_values.append(
            Paragraph(f"<font color='{color_val}'><b>{p_val:.1f}%</b></font>{' (Predicted)' if is_pred else ''}", style_body)
        )

    prob_table = Table([prob_headers, prob_values], colWidths=[176.0, 176.0, 178.0])
    prob_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_TEAL_DARK),
        ("BACKGROUND", (0, 1), (-1, 1), COLOR_BG_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 4.5),
    ]))
    elements.append(prob_table)
    elements.append(Spacer(1, 8))

    # 5. Explainable AI Contributing Factors
    elements.append(Paragraph("3. Explainable AI (XAI) &bull; Influential Input Factors", style_h2))
    raw_factors = assessment_record.get("factors", "[]")
    if isinstance(raw_factors, str):
        try:
            factors = json.loads(raw_factors)
        except Exception:
            factors = []
    elif isinstance(raw_factors, list):
        factors = raw_factors
    else:
        factors = []

    factor_table_data = [
        [
            Paragraph("Clinical Indicator Group", style_table_header),
            Paragraph("Impact Direction", style_table_header),
            Paragraph("Relative Share", style_table_header),
            Paragraph("Human-Readable Context Explanation", style_table_header)
        ]
    ]

    for factor in factors[:5]:  # Display top 5 influential factors
        direction_text = factor.get("direction", "Neutral")
        color_tag = "#dc2626" if "toward" in direction_text.lower() or "risk" in direction_text.lower() else "#16a34a"
        arrow = factor.get("arrow", "&bull;")

        factor_table_data.append([
            Paragraph(f"<b>{arrow} {factor.get('name', '')}</b>", style_table_cell),
            Paragraph(f"<font color='{color_tag}'><b>{direction_text}</b></font>", style_table_cell),
            Paragraph(f"{factor.get('share', 0.0):.1f}%", style_table_cell),
            Paragraph(factor.get("explanation", "-"), style_table_cell)
        ])

    if len(factor_table_data) == 1:
        factor_table_data.append([
            Paragraph("Balanced Profile", style_table_cell),
            Paragraph("Neutral", style_table_cell),
            Paragraph("100.0%", style_table_cell),
            Paragraph("Clinical indicators operate harmoniously within baseline reference boundaries.", style_table_cell)
        ])

    factor_table = Table(factor_table_data, colWidths=[120.0, 100.0, 70.0, 240.0])
    factor_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_TEAL_DARK),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(factor_table)
    elements.append(Spacer(1, 8))

    # 6. Clinical Guidance & Advisory Protocol
    elements.append(Paragraph("4. Recommended Next-Step Clinical Action Protocol", style_h2))
    guidance_data = [[
        Paragraph(f"<b>Protocol Directives:</b> {advice_text}", style_body)
    ]]
    guidance_table = Table(guidance_data, colWidths=[TOTAL_WIDTH])
    guidance_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, COLOR_TEAL),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(guidance_table)
    elements.append(Spacer(1, 6))

    # 7. Official Academic Research & Decision-Support Disclaimer
    elements.append(Paragraph("5. Research Decision-Support & Academic Disclaimer", style_h2))
    disclaimer_p = Paragraph(
        f"<b>IMPORTANT CLINICAL NOTICE:</b> {disclaimer_text} "
        "This assessment report is generated algorithmically by the NutriRisk AI machine learning pipeline "
        f"({model_name}, version {model_version_str}) for screening prioritization and academic evaluation. "
        "It does NOT constitute an autonomous clinical diagnosis, medical prescription, or definitive therapeutic treatment plan. "
        "All predictions and probability breakdowns must be reviewed and corroborated by a licensed healthcare professional, "
        "clinical dietitian, or physician alongside standard laboratory assays.",
        style_body_muted
    )
    elements.append(disclaimer_p)

    # Build document with page decorations
    doc.build(elements, onFirstPage=_draw_page_decorations, onLaterPages=_draw_page_decorations)
    buffer.seek(0)
    return buffer
