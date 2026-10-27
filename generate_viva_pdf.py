"""Export the revised study guide to a readable PDF. Optional: pip install reportlab==4.4.9."""

import argparse
import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent


def inline(text):
    text = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def build_pdf(destination=None):
    destination = Path(destination or ROOT / "output/pdf/FairRecruit_Viva_Guide.pdf")
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="GuideTitle",
            fontName="Times-Roman",
            fontSize=29,
            leading=33,
            textColor=colors.HexColor("#20353b"),
            spaceAfter=15,
        )
    )
    styles.add(
        ParagraphStyle(
            name="GuideHeading",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=19,
            textColor=colors.HexColor("#2e7669"),
            spaceBefore=18,
            spaceAfter=8,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="GuideBody",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#34474b"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="GuideBullet",
            parent=styles["GuideBody"],
            leftIndent=12,
            firstLineIndent=-7,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="GuideCell",
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#34474b"),
        )
    )
    story = []
    lines = (ROOT / "docs/VIVA_GUIDE.md").read_text(encoding="utf-8-sig").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", c) for c in cells):
                    rows.append(cells)
                i += 1
            width = 174 * mm
            widths = [width * 0.48] + [width * 0.52 / (len(rows[0]) - 1)] * (
                len(rows[0]) - 1
            )
            table = Table(
                [
                    [Paragraph(inline(c), styles["GuideCell"]) for c in row]
                    for row in rows
                ],
                colWidths=widths,
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0e5")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f7f8f4")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#cbd7c6")),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["GuideTitle"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["GuideHeading"]))
        elif line.startswith("- "):
            story.append(Paragraph("- " + inline(line[2:]), styles["GuideBullet"]))
        else:
            story.append(KeepTogether([Paragraph(inline(line), styles["GuideBody"])]))
        i += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dae2d5"))
        canvas.line(18 * mm, 17 * mm, 192 * mm, 17 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#607361"))
        canvas.drawString(
            18 * mm, 12 * mm, "FAIRRECRUIT  /  PROJECT 05  /  REVISED VIVA GUIDE"
        )
        canvas.drawRightString(192 * mm, 12 * mm, str(doc.page))
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=24 * mm,
        title="FairRecruit - Revised Viva Guide",
        author="FairRecruit project",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(destination)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--complete", action="store_true", help="Generate the comprehensive 8-page viva handbook.")
    args = parser.parse_args()
    build_pdf(args.output)
    try:
        from generate_complete_viva_pdf import build_complete_viva_guide
        build_complete_viva_guide()
    except Exception as e:
        print(f"Notice: complete guide generation encountered: {e}")
