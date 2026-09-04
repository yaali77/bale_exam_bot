"""
تولید کارنامه PDF کاربر (بخش ۹ چک‌لیست).
شامل: میانگین، تعداد آزمون‌ها، تعداد قبولی، بالاترین/پایین‌ترین نمره، شماره کارنامه، تاریخ صدور، QR.
"""
import os
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from sqlalchemy.orm import Session

from app.config import settings
from app.models.result import Result, ResultStatus


def _generate_report_number(user_national_code: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M")
    return f"RC-{user_national_code[-4:]}-{timestamp}"


def build_report_card_pdf(db: Session, user, qr_image_path: str, report_number: str) -> str:
    """ساخت فایل PDF کارنامه و برگرداندن مسیر آن"""
    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)

    results = (
        db.query(Result)
        .filter(Result.user_id == user.id, Result.status == ResultStatus.PUBLISHED)
        .all()
    )

    scores = [float(r.score) for r in results]
    passed_count = sum(1 for r in results if r.is_passed)
    average = sum(scores) / len(scores) if scores else 0
    highest = max(scores) if scores else 0
    lowest = min(scores) if scores else 0

    file_path = os.path.join(settings.PDF_STORAGE_PATH, f"{report_number}.pdf")
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # هدر
    c.setFillColor(colors.HexColor("#0d3b66"))
    c.rect(0, height - 3 * cm, width, 3 * cm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 1.8 * cm, settings.ORGANIZATION_NAME)
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 2.5 * cm, "Exam Report Card")

    # اطلاعات کاربر
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    y = height - 4.5 * cm
    c.drawString(2 * cm, y, f"Report Number: {report_number}")
    c.drawString(2 * cm, y - 0.7 * cm, f"National Code: {user.national_code}")
    c.drawString(2 * cm, y - 1.4 * cm, f"Issue Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")

    # خلاصه آماری
    y -= 2.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Summary")
    c.setFont("Helvetica", 11)
    stats = [
        f"Total Exams: {len(results)}",
        f"Passed: {passed_count}",
        f"Average Score: {average:.2f}",
        f"Highest Score: {highest:.2f}",
        f"Lowest Score: {lowest:.2f}",
    ]
    for i, line in enumerate(stats):
        c.drawString(2 * cm, y - 0.7 * cm * (i + 1), line)

    # جدول نتایج
    y -= 0.7 * cm * (len(stats) + 2)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Exam")
    c.drawString(10 * cm, y, "Score")
    c.drawString(13 * cm, y, "Status")
    c.line(2 * cm, y - 0.2 * cm, width - 2 * cm, y - 0.2 * cm)

    c.setFont("Helvetica", 10)
    for i, r in enumerate(results):
        row_y = y - 0.7 * cm * (i + 1)
        if row_y < 4 * cm:
            c.showPage()
            row_y = height - 3 * cm
        c.drawString(2 * cm, row_y, str(r.exam.title)[:40])
        c.drawString(10 * cm, row_y, str(r.score))
        c.drawString(13 * cm, row_y, "Passed" if r.is_passed else "Failed")

    # QR اعتبارسنجی در پایین صفحه
    if os.path.exists(qr_image_path):
        c.drawImage(ImageReader(qr_image_path), width - 5 * cm, 2 * cm, width=3 * cm, height=3 * cm)
        c.setFont("Helvetica", 8)
        c.drawString(width - 5 * cm, 1.7 * cm, "Scan to verify")

    c.save()
    return file_path
