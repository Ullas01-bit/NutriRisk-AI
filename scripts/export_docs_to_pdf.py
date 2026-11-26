"""
Export Markdown Documentation to Publication-Quality PDF Reports using ReportLab.
Converts:
  1. REVIEW_1_PREPARATION_DOCUMENT.md -> Prompt25_Review_1_Preparation.pdf
  2. ARCHITECTURE_AND_TECHNICAL_DIAGRAMS.md -> Prompt26_Architecture_and_Technical_Diagrams.pdf
  3. PROJECT_DOCUMENTATION.md -> Prompt27_Complete_Project_Documentation.pdf
  4. VIVA_PREPARATION_GUIDE.md -> Prompt28_Viva_Preparation_Guide.pdf
  5. FINAL_INTEGRATION_REPORT.md -> Prompt29_Final_Integration_Report.pdf
  6. FINAL_PROJECT_COMPLETION_AUDIT.md -> Prompt32_Final_Project_Completion_Audit.pdf
"""
import os
import re
import html
import sys
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    KeepTogether, PageBreak, Image as RLImage
)
from reportlab.pdfgen import canvas

# Palette
COLOR_PRIMARY = colors.HexColor("#0f766e")       # Deep Teal
COLOR_PRIMARY_LIGHT = colors.HexColor("#f0fdfa") # Light Teal
COLOR_DARK = colors.HexColor("#0f172a")          # Slate 900
COLOR_TEXT = colors.HexColor("#1e293b")          # Slate 800
COLOR_MUTED = colors.HexColor("#64748b")         # Slate 500
COLOR_BORDER = colors.HexColor("#cbd5e1")        # Slate 300
COLOR_ROW_ALT = colors.HexColor("#f8fafc")       # Slate 50
COLOR_ACCENT = colors.HexColor("#d97706")        # Amber Accent
COLOR_CODE_BG = colors.HexColor("#f1f5f9")       # Slate 100


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page count and professional header/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(COLOR_MUTED)

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            header_title = getattr(self, "doc_header_title", "NutriRisk AI — Technical Documentation")
            self.drawString(40, 812, header_title)
            self.drawRightString(555, 812, "NutriRisk AI • Clinical Intelligence")
            self.setStrokeColor(COLOR_BORDER)
            self.setLineWidth(0.5)
            self.line(40, 806, 555, 806)

        # Running Footer (all pages)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(555, 25, page_str)
        self.drawString(40, 25, "NutriRisk AI: Predictive Nutritional Risk Assessment • Major Project Dossier")
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(40, 34, 555, 34)

        self.restoreState()


def get_styles():
    """Generates custom typography styles for the PDF document."""
    base = getSampleStyleSheet()
    
    styles = {
        "title": ParagraphStyle(
            "DocTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=COLOR_PRIMARY,
            spaceAfter=8,
            alignment=0
        ),
        "subtitle": ParagraphStyle(
            "DocSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=COLOR_DARK,
            spaceAfter=12
        ),
        "h1": ParagraphStyle(
            "Heading1_Custom",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=COLOR_PRIMARY,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        ),
        "h2": ParagraphStyle(
            "Heading2_Custom",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=COLOR_DARK,
            spaceBefore=12,
            spaceAfter=5,
            keepWithNext=True
        ),
        "h3": ParagraphStyle(
            "Heading3_Custom",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=COLOR_PRIMARY,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        ),
        "h4": ParagraphStyle(
            "Heading4_Custom",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=COLOR_DARK,
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True
        ),
        "body": ParagraphStyle(
            "Body_Custom",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12.5,
            textColor=COLOR_TEXT,
            spaceAfter=5
        ),
        "bullet": ParagraphStyle(
            "Bullet_Custom",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=COLOR_TEXT,
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=3
        ),
        "number_list": ParagraphStyle(
            "NumList_Custom",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=COLOR_TEXT,
            leftIndent=18,
            firstLineIndent=-14,
            spaceAfter=3
        ),
        "callout": ParagraphStyle(
            "Callout_Custom",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=12,
            textColor=COLOR_DARK,
            spaceBefore=4,
            spaceAfter=4
        ),
        "code_inline": ParagraphStyle(
            "CodeInline",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=COLOR_PRIMARY
        ),
        "code_block": ParagraphStyle(
            "CodeBlock",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=COLOR_DARK
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=colors.white,
            alignment=0
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT,
            alignment=0
        ),
        "table_cell_bold": ParagraphStyle(
            "TableCellBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=COLOR_DARK,
            alignment=0
        )
    }
    return styles


def safe_paragraph(text: str, style, raw_fallback: str = ""):
    """Safely creates a Paragraph flowable. If ReportLab XML parsing fails, falls back to plain text."""
    try:
        return Paragraph(text, style)
    except Exception as e:
        clean = html.escape(re.sub(r"<[^>]+>", "", raw_fallback or text))
        return Paragraph(clean, style)


def format_inline_markdown(text: str) -> str:
    """Escapes HTML and converts inline markdown syntax into ReportLab supported tags."""
    if not text:
        return ""
    
    # 1. Protect inline code `code` first with unique tokens so underscores are never touched
    code_tokens = []
    def code_repl(m):
        code_content = m.group(1)
        token = f"__CODETOKEN{len(code_tokens)}__"
        escaped = html.escape(code_content)
        code_tokens.append(f'<font face="Courier" color="#0f766e"><b>{escaped}</b></font>')
        return token

    text_no_code = re.sub(r"`([^`]+)`", code_repl, text)

    # 2. Protect math $...$
    math_tokens = []
    def math_repl(m):
        math_content = m.group(1)
        token = f"__MATHTOKEN{len(math_tokens)}__"
        math_tokens.append(f'<i>{html.escape(math_content)}</i>')
        return token

    text_no_math = re.sub(r"\$([^$]+)\$", math_repl, text_no_code)

    # 3. Escape raw XML special characters
    s = html.escape(text_no_math.strip())

    # 4. Markdown links [text](url) -> formatted text
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r'<font color="#0d9488"><u>\1</u></font>', s)

    # 5. Bold **text**
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)

    # 6. Italic *text* (asterisk only, avoiding intra-word underscores)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)

    # 7. Italic with underscores only when at word boundary
    s = re.sub(r"(^|\s)_([^_]+)_(?=\s|[.,:;!?]|$)", r"\1<i>\2</i>", s)

    # 8. Re-inject math tokens
    for i, tok in enumerate(math_tokens):
        s = s.replace(f"__MATHTOKEN{i}__", tok)

    # 9. Re-inject code tokens
    for i, tok in enumerate(code_tokens):
        s = s.replace(f"__CODETOKEN{i}__", tok)

    return s


def parse_markdown_table(table_lines, styles, max_width=515):
    """Parses markdown table lines into a ReportLab Table flowable with wrapped paragraphs."""
    parsed_rows = []
    for line in table_lines:
        line_clean = line.strip()
        if not line_clean.startswith("|"):
            continue
        # Split cells by pipe
        raw_cells = [c.strip() for c in line_clean.strip("|").split("|")]
        
        # Check if delimiter row
        if all(re.match(r"^:?-+:?$", c) for c in raw_cells):
            continue
            
        parsed_rows.append(raw_cells)

    if not parsed_rows:
        return None

    # Normalize column count
    num_cols = max(len(row) for row in parsed_rows)
    norm_rows = []
    for row in parsed_rows:
        padded = row + [""] * (num_cols - len(row))
        norm_rows.append(padded)

    # Estimate column widths based on length of content
    col_max_lens = [3] * num_cols
    for row in norm_rows:
        for i, cell in enumerate(row):
            col_max_lens[i] = max(col_max_lens[i], len(cell))
            
    total_len = sum(col_max_lens)
    col_widths = [(l / total_len) * max_width for l in col_max_lens]
    # Bound minimum column width
    min_col_w = 40
    for i in range(num_cols):
        if col_widths[i] < min_col_w:
            col_widths[i] = min_col_w
    # Re-normalize to max_width
    curr_total = sum(col_widths)
    col_widths = [(w / curr_total) * max_width for w in col_widths]

    # Convert cells to Paragraph flowables
    table_data = []
    for row_idx, row in enumerate(norm_rows):
        row_data = []
        is_header = (row_idx == 0)
        for cell_text in row:
            formatted = format_inline_markdown(cell_text)
            if is_header:
                p = safe_paragraph(formatted, styles["table_header"], cell_text)
            elif cell_text.startswith("**") and cell_text.endswith("**"):
                p = safe_paragraph(formatted, styles["table_cell_bold"], cell_text)
            else:
                p = safe_paragraph(formatted, styles["table_cell"], cell_text)
            row_data.append(p)
        table_data.append(row_data)

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("BOX", (0, 0), (-1, -1), 0.75, COLOR_PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    # Alternating row background
    for r in range(1, len(table_data)):
        bg = COLOR_ROW_ALT if r % 2 == 1 else colors.white
        t_style.append(("BACKGROUND", (0, r), (-1, r), bg))
        
    t.setStyle(TableStyle(t_style))
    return t


def convert_markdown_to_flowables(md_content: str, styles, base_dir: str):
    """Converts a full markdown document into a list of ReportLab Flowables."""
    flowables = []
    lines = md_content.splitlines()
    
    i = 0
    in_code_block = False
    code_block_lines = []
    code_lang = ""
    table_lines = []

    # Detect title if first line is #
    doc_title_extracted = ""
    last_heading = ""

    # Diagram mapping table
    diagram_map = {
        "overall system architecture": "diag01_system_architecture.png",
        "system architecture": "diag01_system_architecture.png",
        "level 0": "diag02_dfd_level_0.png",
        "level 1": "diag03_dfd_level_1.png",
        "ml workflow": "diag04_ml_workflow.png",
        "machine learning workflow": "diag04_ml_workflow.png",
        "use case": "diag05_use_case.png",
        "er diagram": "diag06_database_er.png",
        "entity-relationship": "diag06_database_er.png",
        "sequence diagram": "diag07_sequence_diagram.png",
        "activity diagram": "diag08_activity_diagram.png",
        "training pipeline": "diag09_training_pipeline.png",
        "risk prediction": "diag10_prediction_xai_workflow.png",
        "explainability": "diag10_prediction_xai_workflow.png",
        "proposed methodology": "diag01_system_architecture.png"
    }

    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()

        # 1. Handle Code Blocks (```)
        if line_stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = line_stripped[3:].strip()
                code_block_lines = []
                i += 1
                continue
            else:
                # End of code block
                in_code_block = False
                code_text = "\n".join(code_block_lines)
                escaped_code = html.escape(code_text)
                
                label_text = f"<b>Code ({code_lang})</b>" if code_lang else "<b>Code Block</b>"
                if "mermaid" in code_lang.lower():
                    label_text = "<b>Mermaid Architecture Specification</b>"

                    # Map to rendered visual image
                    matched_img = None
                    lh_clean = last_heading.lower()
                    for k, img_name in diagram_map.items():
                        if k in lh_clean:
                            matched_img = img_name
                            break
                    if not matched_img:
                        ct_lower = code_text.lower()
                        if "erdiagram" in ct_lower or "db_users" in ct_lower:
                            matched_img = "diag06_database_er.png"
                        elif "sequencediagram" in ct_lower:
                            matched_img = "diag07_sequence_diagram.png"
                        elif "actor" in ct_lower or "usecase" in ct_lower:
                            matched_img = "diag05_use_case.png"
                        elif "0.0" in ct_lower and "nutririsk" in ct_lower:
                            matched_img = "diag02_dfd_level_0.png"
                        elif "1.0" in ct_lower and "persist" in ct_lower:
                            matched_img = "diag03_dfd_level_1.png"
                        elif "stratified" in ct_lower or "benchmark" in ct_lower:
                            matched_img = "diag09_training_pipeline.png"
                        elif "occlusion" in ct_lower or "probabilities" in ct_lower:
                            matched_img = "diag10_prediction_xai_workflow.png"
                        elif "datapipeline" in ct_lower or "mlcore" in ct_lower:
                            matched_img = "diag04_ml_workflow.png"
                        else:
                            matched_img = "diag01_system_architecture.png"

                    img_path = os.path.join(r"D:\MAJOR PROJECT\reports\diagrams", matched_img)
                    if os.path.exists(img_path):
                        try:
                            with PILImage.open(img_path) as pil_im:
                                w, h = pil_im.size
                                aspect = h / w
                                target_w = 490
                                target_h = target_w * aspect
                                flowables.append(Spacer(1, 6))
                                flowables.append(RLImage(img_path, width=target_w, height=target_h))
                                caption_title = last_heading or "Technical Architecture Diagram"
                                caption_p = safe_paragraph(f"<b>Figure: {html.escape(caption_title)} (Rendered Visual Graphic)</b>", styles["callout"])
                                flowables.append(caption_p)
                                flowables.append(Spacer(1, 6))
                        except Exception as ex:
                            print(f"Warning: could not insert diagram image {img_path}: {ex}")

                header_p = safe_paragraph(label_text, styles["table_header"])
                code_p = safe_paragraph(f"<pre>{escaped_code}</pre>", styles["code_block"], escaped_code)
                
                block_table = Table(
                    [[header_p], [code_p]],
                    colWidths=[515]
                )
                block_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                    ("BACKGROUND", (0, 1), (-1, 1), COLOR_CODE_BG),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                flowables.append(Spacer(1, 4))
                flowables.append(block_table)
                flowables.append(Spacer(1, 6))
                i += 1
                continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # 2. Handle Markdown Tables (| ... |)
        if line_stripped.startswith("|") and "|" in line_stripped[1:]:
            table_lines.append(line)
            # Peek next line to see if table continues
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                i += 1
                continue
            else:
                # End of table
                t_flowable = parse_markdown_table(table_lines, styles)
                if t_flowable:
                    flowables.append(Spacer(1, 4))
                    flowables.append(t_flowable)
                    flowables.append(Spacer(1, 6))
                table_lines = []
                i += 1
                continue

        # 3. Handle Horizontal Rules (--- or ***)
        if re.match(r"^(\-{3,}|\*{3,})$", line_stripped):
            flowables.append(Spacer(1, 4))
            flowables.append(HRFlowable(width="100%", thickness=0.8, color=COLOR_PRIMARY, spaceBefore=4, spaceAfter=8))
            i += 1
            continue

        # 4. Handle Headings
        if line_stripped.startswith("#"):
            match = re.match(r"^(#{1,6})\s+(.*)$", line_stripped)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                last_heading = text
                formatted_text = format_inline_markdown(text)

                if level == 1:
                    # Document main title
                    doc_title_extracted = text
                    flowables.append(safe_paragraph(formatted_text, styles["title"], text))
                    flowables.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY, spaceBefore=2, spaceAfter=8))
                elif level == 2:
                    # Check if chapter starts -> PageBreak if substantial
                    if text.startswith("CHAPTER") or text.startswith("SECTION"):
                        flowables.append(PageBreak())
                    flowables.append(Spacer(1, 6))
                    flowables.append(safe_paragraph(formatted_text, styles["h1"], text))
                elif level == 3:
                    flowables.append(safe_paragraph(formatted_text, styles["h2"], text))
                elif level == 4:
                    flowables.append(safe_paragraph(formatted_text, styles["h3"], text))
                else:
                    flowables.append(safe_paragraph(formatted_text, styles["h4"], text))
                i += 1
                continue

        # 5. Handle Blockquotes (> ...)
        if line_stripped.startswith(">"):
            quote_text = line_stripped.lstrip("> ").strip()
            formatted_quote = format_inline_markdown(quote_text)
            p = safe_paragraph(formatted_quote, styles["callout"], quote_text)
            quote_box = Table([[p]], colWidths=[515])
            quote_box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARY_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3, COLOR_PRIMARY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            flowables.append(Spacer(1, 3))
            flowables.append(quote_box)
            flowables.append(Spacer(1, 3))
            i += 1
            continue

        # 6. Handle Bullet Lists (- ... or * ...)
        bullet_match = re.match(r"^[-*]\s+(.*)$", line_stripped)
        if bullet_match:
            bullet_text = bullet_match.group(1).strip()
            formatted = format_inline_markdown(bullet_text)
            flowables.append(safe_paragraph(f"•&nbsp;&nbsp;{formatted}", styles["bullet"], f"•  {bullet_text}"))
            i += 1
            continue

        # 7. Handle Numbered Lists (1. ... or 2. ...)
        num_match = re.match(r"^(\d+)\.\s+(.*)$", line_stripped)
        if num_match:
            num = num_match.group(1)
            num_text = num_match.group(2).strip()
            formatted = format_inline_markdown(num_text)
            flowables.append(safe_paragraph(f"<b>{num}.</b>&nbsp;&nbsp;{formatted}", styles["number_list"], f"{num}. {num_text}"))
            i += 1
            continue

        # 8. Handle Image references ![alt](path)
        img_match = re.search(r"!\[(.*?)\]\((.*?)\)", line_stripped)
        if img_match:
            alt_text = img_match.group(1)
            img_rel_path = img_match.group(2).strip()
            # Try finding image in base_dir, current dir, reports dir, reports/diagrams
            candidates = [
                img_rel_path,
                os.path.join(base_dir, img_rel_path),
                os.path.join("reports", os.path.basename(img_rel_path)),
                os.path.join(r"D:\MAJOR PROJECT\reports\diagrams", os.path.basename(img_rel_path)),
                os.path.join(r"D:\MAJOR PROJECT\reports", os.path.basename(img_rel_path)),
                os.path.join("data", os.path.basename(img_rel_path)),
                os.path.join(r"C:\Users\ashok\.gemini\antigravity\brain\44422476-581e-429c-832a-13be1f058813", os.path.basename(img_rel_path))
            ]
            found_img = None
            for cand in candidates:
                if os.path.exists(cand) and cand.lower().endswith((".png", ".jpg", ".jpeg")):
                    found_img = cand
                    break
            
            if found_img:
                try:
                    with PILImage.open(found_img) as pil_im:
                        w, h = pil_im.size
                        aspect = h / w
                        target_w = min(480, w)
                        target_h = target_w * aspect
                        flowables.append(Spacer(1, 4))
                        flowables.append(RLImage(found_img, width=target_w, height=target_h))
                        if alt_text:
                            caption = safe_paragraph(f"<i>Figure: {html.escape(alt_text)}</i>", styles["callout"], alt_text)
                            flowables.append(caption)
                        flowables.append(Spacer(1, 6))
                except Exception as ex:
                    print(f"Warning: could not render image {found_img}: {ex}")
            i += 1
            continue

        # 9. Handle Regular Paragraphs
        if line_stripped:
            formatted = format_inline_markdown(line_stripped)
            flowables.append(safe_paragraph(formatted, styles["body"], line_stripped))
        else:
            flowables.append(Spacer(1, 3))

        i += 1

    return flowables, doc_title_extracted


def generate_pdf_from_markdown(md_path: str, pdf_path: str, doc_category: str):
    """Compiles a single markdown document into a clean, numbered PDF report."""
    print(f"[*] Processing: {os.path.basename(md_path)} -> {os.path.basename(pdf_path)}...")
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    styles = get_styles()
    base_dir = os.path.dirname(md_path)
    flowables, extracted_title = convert_markdown_to_flowables(content, styles, base_dir)

    # Setup SimpleDocTemplate
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=46,
        bottomMargin=46
    )

    # Use NumberedCanvas for header/footers
    def canvas_maker(*args, **kwargs):
        c = NumberedCanvas(*args, **kwargs)
        c.doc_header_title = f"NutriRisk AI — {doc_category}"
        return c

    doc.build(flowables, canvasmaker=canvas_maker)
    size_kb = os.path.getsize(pdf_path) / 1024
    print(f"[OK] Created: {pdf_path} ({size_kb:.1f} KB)")


def main():
    artifact_dir = r"C:\Users\ashok\.gemini\antigravity\brain\44422476-581e-429c-832a-13be1f058813"
    out_dir = r"D:\MAJOR PROJECT\pdf_reports"
    os.makedirs(out_dir, exist_ok=True)

    tasks = [
        {
            "prompt": "Prompt 25",
            "md": os.path.join(artifact_dir, "REVIEW_1_PREPARATION_DOCUMENT.md"),
            "pdf": os.path.join(out_dir, "Prompt25_Review_1_Preparation.pdf"),
            "category": "Review 1 Preparation Dossier"
        },
        {
            "prompt": "Prompt 26",
            "md": os.path.join(artifact_dir, "ARCHITECTURE_AND_TECHNICAL_DIAGRAMS.md"),
            "pdf": os.path.join(out_dir, "Prompt26_Architecture_and_Technical_Diagrams.pdf"),
            "category": "Architecture & Technical Diagrams Specification"
        },
        {
            "prompt": "Prompt 27",
            "md": os.path.join(artifact_dir, "PROJECT_DOCUMENTATION.md"),
            "pdf": os.path.join(out_dir, "Prompt27_Complete_Project_Documentation.pdf"),
            "category": "Academic Project Documentation (17 Chapters)"
        },
        {
            "prompt": "Prompt 28",
            "md": os.path.join(artifact_dir, "VIVA_PREPARATION_GUIDE.md"),
            "pdf": os.path.join(out_dir, "Prompt28_Viva_Preparation_Guide.pdf"),
            "category": "Oral Defense & Viva Voce Master Guide (100 Q&As)"
        },
        {
            "prompt": "Prompt 29",
            "md": os.path.join(artifact_dir, "FINAL_INTEGRATION_REPORT.md"),
            "pdf": os.path.join(out_dir, "Prompt29_Final_Integration_Report.pdf"),
            "category": "Full-Stack System Integration Report"
        },
        {
            "prompt": "Prompt 32",
            "md": os.path.join(artifact_dir, "FINAL_PROJECT_COMPLETION_AUDIT.md"),
            "pdf": os.path.join(out_dir, "Prompt32_Final_Project_Completion_Audit.pdf"),
            "category": "Final Project Completion Audit & Certification"
        }
    ]

    print("=" * 70)
    print("NutriRisk AI: Generating Separate PDF Documents for Prompts 25, 26, 27, 28, 29, 32")
    print("=" * 70)

    generated_files = []
    for t in tasks:
        if not os.path.exists(t["md"]):
            print(f"[!] Error: Source markdown not found at {t['md']}")
            continue
        generate_pdf_from_markdown(t["md"], t["pdf"], t["category"])
        generated_files.append((t["prompt"], t["category"], t["pdf"], os.path.getsize(t["pdf"]) / 1024))

    print("\n" + "=" * 70)
    print("Generation Completed Successfully! Summary:")
    print("=" * 70)
    for p, cat, path, size in generated_files:
        print(f" * {p}: {os.path.basename(path)} ({size:.1f} KB) - {cat}")
    print("=" * 70)


if __name__ == "__main__":
    main()
