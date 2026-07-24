"""Generate the CampusAgent enrollment-certificate demo PDF.

The document is deliberately marked as a non-official demo artifact. It is
generated with reportlab inside the repository-managed uv environment.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PDF = ROOT / "output" / "pdf" / "enrollment_certificate_demo.pdf"
PUBLIC_PDF = ROOT / "apps" / "web" / "public" / "demo" / "enrollment-certificate-demo.pdf"
LOGO = ROOT / "apps" / "web" / "public" / "brand" / "jinan-university-logo.png"


def register_fonts() -> tuple[str, str]:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    ]
    for font_path in candidates:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("CampusChinese", str(font_path)))
            return "CampusChinese", "CampusChinese"
    return "Helvetica", "Helvetica-Bold"


def centered_text(pdf: canvas.Canvas, text: str, y: float, font: str, size: float, color: colors.Color) -> None:
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    pdf.drawCentredString(A4[0] / 2, y, text)


def draw_demo_stamp(pdf: canvas.Canvas, x: float, y: float) -> None:
    pdf.saveState()
    pdf.setStrokeColor(colors.HexColor("#B34A42"))
    pdf.setFillColor(colors.HexColor("#B34A42"))
    pdf.setLineWidth(2)
    pdf.circle(x, y, 42, stroke=1, fill=0)
    pdf.circle(x, y, 35, stroke=1, fill=0)
    pdf.setFont("CampusChinese", 13)
    pdf.drawCentredString(x, y + 7, "演示件")
    pdf.setFont("CampusChinese", 9)
    pdf.drawCentredString(x, y - 11, "非官方证明")
    pdf.restoreState()


def build_pdf(destination: Path) -> None:
    regular_font, bold_font = register_fonts()
    destination.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(destination), pagesize=A4, pageCompression=1)
    width, height = A4
    pdf.setTitle("CampusAgent 在读证明演示件")
    pdf.setAuthor("CampusAgent Demo")
    pdf.setSubject("非官方在读证明功能演示")

    pdf.setFillColor(colors.HexColor("#FAFBF8"))
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    # Strong watermark prevents the demo from being mistaken for an official certificate.
    pdf.saveState()
    pdf.translate(width / 2, height / 2)
    pdf.rotate(34)
    pdf.setFillColor(colors.Color(0.69, 0.26, 0.23, alpha=0.09))
    pdf.setFont(bold_font, 58)
    pdf.drawCentredString(0, 0, "演示件 · 非官方证明")
    pdf.restoreState()

    pdf.setFillColor(colors.HexColor("#087D78"))
    pdf.rect(0, height - 8, width, 8, stroke=0, fill=1)

    logo_reader = ImageReader(str(LOGO))
    logo_width = 220
    logo_height = logo_width * 313 / 929
    pdf.drawImage(logo_reader, 54, height - 104, width=logo_width, height=logo_height, mask="auto", preserveAspectRatio=True)

    pdf.setFillColor(colors.HexColor("#63736A"))
    pdf.setFont(regular_font, 9)
    pdf.drawRightString(width - 54, height - 68, "CampusAgent 校园事务演示")
    pdf.setFillColor(colors.HexColor("#A34B43"))
    pdf.drawRightString(width - 54, height - 84, "DEMO · NOT AN OFFICIAL DOCUMENT")

    pdf.setStrokeColor(colors.HexColor("#D9E1DC"))
    pdf.setLineWidth(1)
    pdf.line(54, height - 122, width - 54, height - 122)

    centered_text(pdf, "在 读 证 明", height - 178, bold_font, 26, colors.HexColor("#24352C"))
    centered_text(pdf, "CERTIFICATE OF ENROLLMENT · DEMO", height - 201, regular_font, 10, colors.HexColor("#718078"))

    body_x = 76
    body_top = height - 260
    pdf.setFillColor(colors.HexColor("#34483D"))
    pdf.setFont(regular_font, 13)
    lines = [
        "兹证明 Alice Chen（演示学生），学号 2026100001，系暨南大学信息科学技术学院",
        "软件工程专业全日制本科生，于 2026 年 9 月入学，预计于 2030 年 6 月毕业。",
        "截至本演示文件生成之日，该生在读状态为：在籍。",
        "本证明用途：实习材料演示。",
    ]
    for index, line in enumerate(lines):
        pdf.drawString(body_x, body_top - index * 34, line)

    pdf.setFillColor(colors.HexColor("#5C6C63"))
    pdf.setFont(regular_font, 11)
    pdf.drawString(body_x, body_top - 158, "This document certifies the demo enrollment status shown above.")

    info_y = 300
    pdf.setFillColor(colors.HexColor("#EDF4F0"))
    pdf.roundRect(64, info_y, width - 128, 88, 10, stroke=0, fill=1)
    pdf.setFillColor(colors.HexColor("#376756"))
    pdf.setFont(bold_font, 11)
    pdf.drawString(80, info_y + 62, "演示申请信息")
    pdf.setFillColor(colors.HexColor("#5E6F65"))
    pdf.setFont(regular_font, 10)
    pdf.drawString(80, info_y + 40, "演示编号：JNU-DEMO-20260721-018")
    pdf.drawString(80, info_y + 21, "生成时间：2026 年 7 月 21 日  ·  文件语言：中文")
    pdf.setFillColor(colors.HexColor("#8A5E35"))
    pdf.drawRightString(width - 80, info_y + 40, "无真实受理号")
    pdf.drawRightString(width - 80, info_y + 21, "不可用于身份或学籍核验")

    draw_demo_stamp(pdf, width - 118, 211)
    pdf.setFillColor(colors.HexColor("#3E5046"))
    pdf.setFont(regular_font, 11)
    pdf.drawString(76, 225, "CampusAgent 演示服务")
    pdf.setFillColor(colors.HexColor("#78857D"))
    pdf.setFont(regular_font, 9)
    pdf.drawString(76, 207, "生成日期：2026 年 7 月 21 日")

    pdf.setFillColor(colors.HexColor("#F5E9E6"))
    pdf.roundRect(54, 92, width - 108, 60, 8, stroke=0, fill=1)
    pdf.setFillColor(colors.HexColor("#9D493F"))
    pdf.setFont(bold_font, 11)
    pdf.drawCentredString(width / 2, 126, "此文件仅用于 CampusAgent 功能演示，不具有任何证明效力")
    pdf.setFont(regular_font, 9)
    pdf.drawCentredString(width / 2, 107, "真实证明必须由暨南大学相应责任部门审核并通过学校正式渠道签发。")

    pdf.setStrokeColor(colors.HexColor("#DDE4DF"))
    pdf.line(54, 70, width - 54, 70)
    pdf.setFillColor(colors.HexColor("#8A958E"))
    pdf.setFont(regular_font, 8)
    pdf.drawString(54, 51, "CampusAgent · 暨南大学智能校园管理与协作平台 · 演示文件")
    pdf.drawRightString(width - 54, 51, "第 1 页 / 共 1 页")

    pdf.showPage()
    pdf.save()


def main() -> None:
    build_pdf(OUTPUT_PDF)
    PUBLIC_PDF.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUTPUT_PDF, PUBLIC_PDF)
    print(OUTPUT_PDF)
    print(PUBLIC_PDF)


if __name__ == "__main__":
    main()
