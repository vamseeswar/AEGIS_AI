"""AEGIS AI — Enterprise PDF Generation Engine
Generates publication-grade, corporate executive intelligence reports using ReportLab.
Includes custom brand typography, KPI callout matrices, executive summary blocks,
structured markdown translation, and page numbering.
"""

import io
import re
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that adds running header and 'Page X of Y' footer."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

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

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "AEGIS AI — EXECUTIVE INTELLIGENCE REPORT")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)

        # Running Footer (all pages)
        self.setFont("Helvetica", 8)
        self.drawString(54, 36, "CONFIDENTIAL & PROPRIETARY — STRICT TENANT AUTHORIZATION REQUIRED")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)

        self.restoreState()


def generate_executive_pdf(
    *,
    title: str,
    summary: str | None,
    content_markdown: str,
    metrics: dict[str, Any] | None = None,
    organization_name: str = "Enterprise Organization",
    author_name: str = "AEGIS AI Autonomous Supervisor",
) -> bytes:
    """Compiles an executive briefing into a styled PDF binary buffer."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    primary_color = colors.HexColor("#0F172A")  # Deep slate/navy
    accent_teal = colors.HexColor("#0D9488")    # Teal accent
    slate_muted = colors.HexColor("#475569")    # Muted text
    card_bg = colors.HexColor("#F8FAFC")        # Light neutral background
    border_color = colors.HexColor("#CBD5E1")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=slate_muted,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=accent_teal,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        leftIndent=15,
        spaceAfter=3,
    )

    story: list[Any] = []

    # 1. Document Header Banner
    story.append(Paragraph(title, title_style))
    metadata_line = f"Organization: <b>{organization_name}</b> &nbsp;|&nbsp; Prepared by: <b>{author_name}</b>"
    story.append(Paragraph(metadata_line, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_teal, spaceAfter=14))

    # 2. Executive Summary Callout Box (if provided)
    if summary:
        summary_html = f"<b>EXECUTIVE SUMMARY:</b><br/>{summary}"
        summary_p = Paragraph(summary_html, body_style)
        summary_table = Table([[summary_p]], colWidths=[504])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), card_bg),
                    ("BOX", (0, 0), (-1, -1), 1, border_color),
                    ("LINELEFT", (0, 0), (0, 0), 4, accent_teal),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 14))

    # 3. Key Metrics KPI Table (if provided)
    if metrics and len(metrics) > 0:
        story.append(Paragraph("Key Performance & Operational Metrics", h1_style))
        story.append(Spacer(1, 4))

        # Format metrics into grid rows (up to 4 per row)
        items = list(metrics.items())
        metric_cells = []
        for k, v in items:
            formatted_val = f"{v:,.2f}" if isinstance(v, int | float) and not isinstance(v, bool) else str(v)
            cell_p = Paragraph(
                f"<font size='7.5' color='#64748B'>{k.replace('_', ' ').upper()}</font><br/><font size='13' color='#0F172A'><b>{formatted_val}</b></font>",
                body_style,
            )
            metric_cells.append(cell_p)

        # Chunk into rows of 3
        chunk_size = 3
        table_data = [metric_cells[i : i + chunk_size] for i in range(0, len(metric_cells), chunk_size)]
        # Pad last row if uneven
        while len(table_data[-1]) < chunk_size:
            table_data[-1].append(Paragraph("", body_style))

        kpi_table = Table(table_data, colWidths=[504 / chunk_size] * chunk_size)
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), card_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 14))

    # 4. Structured Content parsed from Markdown
    lines = content_markdown.splitlines()
    in_table = False
    table_raw_rows: list[list[str]] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if in_table and table_raw_rows:
                # Flush accumulated table
                story.append(_build_markdown_table(table_raw_rows, body_style))
                story.append(Spacer(1, 8))
                table_raw_rows = []
                in_table = False
            continue

        # Markdown Table Row
        if line.startswith("|") and line.endswith("|"):
            in_table = True
            # Ignore separator row (|---|---|)
            if re.match(r"^\|[\s\-:|]+\|$", line):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            table_raw_rows.append(cells)
            continue
        elif in_table and table_raw_rows:
            story.append(_build_markdown_table(table_raw_rows, body_style))
            story.append(Spacer(1, 8))
            table_raw_rows = []
            in_table = False

        # Heading 1 (# ...)
        if line.startswith("# "):
            text = _format_inline_markdown(line[2:].strip())
            story.append(Paragraph(text, h1_style))
        # Heading 2 (## ...)
        elif line.startswith("## "):
            text = _format_inline_markdown(line[3:].strip())
            story.append(Paragraph(text, h2_style))
        # Heading 3 (### ...)
        elif line.startswith("### "):
            text = _format_inline_markdown(line[4:].strip())
            h3_style = ParagraphStyle("H3", parent=h2_style, fontSize=10.5, textColor=colors.HexColor("#334155"))
            story.append(Paragraph(text, h3_style))
        # Bullet list item (- ... or * ...)
        elif line.startswith("- ") or line.startswith("* "):
            text = _format_inline_markdown(line[2:].strip())
            bullet_html = f"&bull;&nbsp; {text}"
            story.append(Paragraph(bullet_html, bullet_style))
        # Numbered list (1. ...)
        elif re.match(r"^\d+\.\s", line):
            text = _format_inline_markdown(re.sub(r"^\d+\.\s", "", line))
            num = line.split(".")[0]
            num_html = f"<b>{num}.</b>&nbsp; {text}"
            story.append(Paragraph(num_html, bullet_style))
        # Horizontal Rule
        elif line in ("---", "***", "___"):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceAfter=8))
        # Standard Body Paragraph
        else:
            text = _format_inline_markdown(line)
            story.append(Paragraph(text, body_style))

    # Flush any trailing table
    if in_table and table_raw_rows:
        story.append(_build_markdown_table(table_raw_rows, body_style))

    # Build the document with running header/footer
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def _format_inline_markdown(text: str) -> str:
    """Escapes XML entities and converts markdown bold/italic/code tags to ReportLab tags."""
    # Convert special characters safely
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold **text** -> <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic *text* or _text_ -> <i>text</i>
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # Inline code `code` -> <font color="#0D9488"><code>code</code></font>
    text = re.sub(r"`(.+?)`", r"<font color='#0D9488' face='Courier'><b>\1</b></font>", text)
    return text


def _build_markdown_table(raw_rows: list[list[str]], body_style: ParagraphStyle) -> Table:
    """Transforms raw markdown table text rows into a ReportLab Table with styling."""
    if not raw_rows:
        return Table([[""]])

    col_count = max(len(r) for r in raw_rows)
    col_width = 504 / col_count

    formatted_rows = []
    for row_idx, row in enumerate(raw_rows):
        # Pad row if incomplete
        while len(row) < col_count:
            row.append("")
        row_cells = []
        for cell in row:
            if row_idx == 0:
                p = Paragraph(f"<b>{_format_inline_markdown(cell)}</b>", body_style)
            else:
                p = Paragraph(_format_inline_markdown(cell), body_style)
            row_cells.append(p)
        formatted_rows.append(row_cells)

    t = Table(formatted_rows, colWidths=[col_width] * col_count)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t
