"""
تولید و اعتبارسنجی کارنامه PDF + QR (بخش ۹ و ۱۰ چک‌لیست).
شامل یک Endpoint عمومی /verify/{code} که بدون نیاز به احراز هویت، صرفاً حداقل اطلاعات لازم را نشان می‌دهد.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission, get_current_admin
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.report_card import ReportCard
from app.models.user import User
from app.services.pdf_service import build_report_card_pdf, _generate_report_number
from app.services.qr_service import generate_qr_image, generate_verification_code

router = APIRouter(tags=["Report Card & Verification"])


def generate_or_refresh_report_card(db: Session, user: User) -> ReportCard:
    """
    منطق مشترک ساخت/به‌روزرسانی کارنامه. مستقیماً توسط بات (فراخوانی داخلی، بدون HTTP)
    و توسط Endpoint پنل ادمین (زیر) استفاده می‌شود.
    """
    report_card = db.query(ReportCard).filter(ReportCard.user_id == user.id).first()
    if not report_card:
        report_card = ReportCard(
            user_id=user.id,
            report_number=_generate_report_number(user.national_code),
            verification_code=generate_verification_code(),
        )
        db.add(report_card)
        db.commit()
        db.refresh(report_card)

    qr_path = generate_qr_image(report_card.verification_code)
    pdf_path = build_report_card_pdf(db, user, qr_path, report_card.report_number)

    report_card.qr_path = qr_path
    report_card.pdf_path = pdf_path
    db.commit()
    db.refresh(report_card)
    return report_card


@router.post("/api/users/{user_id}/report-card")
def generate_report_card(user_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("view"))):
    """تولید یا به‌روزرسانی کارنامه PDF یک کاربر از پنل ادمین"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")

    report_card = generate_or_refresh_report_card(db, user)

    log_action(db, action="report_card_generated", actor_type="admin", actor_id=str(admin.id),
               target_type="user", target_id=str(user.id), new_value=report_card.report_number)

    return {"report_number": report_card.report_number, "pdf_path": report_card.pdf_path, "verification_code": report_card.verification_code}


@router.get("/api/users/{user_id}/report-card/download")
def download_report_card(user_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    report_card = db.query(ReportCard).filter(ReportCard.user_id == user_id).first()
    if not report_card or not report_card.pdf_path:
        raise HTTPException(status_code=404, detail="کارنامه‌ای برای این کاربر یافت نشد")
    return FileResponse(report_card.pdf_path, media_type="application/pdf", filename=f"{report_card.report_number}.pdf")


@router.get("/verify/{verification_code}")
def verify_report_card(verification_code: str, db: Session = Depends(get_db)):
    """
    صفحه/API عمومی اعتبارسنجی کارنامه از طریق اسکن QR.
    فقط حداقل اطلاعات لازم نمایش داده می‌شود (بدون کد ملی کامل یا اطلاعات حساس).
    """
    report_card = db.query(ReportCard).filter(ReportCard.verification_code == verification_code).first()
    if not report_card:
        raise HTTPException(status_code=404, detail="کد اعتبارسنجی نامعتبر است")

    log_action(db, action="report_card_verified", actor_type="public",
               target_type="report_card", target_id=str(report_card.id))

    if not report_card.is_valid:
        return {"valid": False, "message": "این کارنامه ابطال شده است"}

    user = db.query(User).filter(User.id == report_card.user_id).first()
    masked_code = f"{user.national_code[:3]}****{user.national_code[-3:]}"

    return {
        "valid": True,
        "report_number": report_card.report_number,
        "national_code_masked": masked_code,
        "issued_at": report_card.issued_at,
    }


@router.post("/api/report-cards/{report_card_id}/void")
def void_report_card(report_card_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("delete"))):
    report_card = db.query(ReportCard).filter(ReportCard.id == report_card_id).first()
    if not report_card:
        raise HTTPException(status_code=404, detail="کارنامه یافت نشد")
    report_card.is_valid = False
    db.commit()
    log_action(db, action="report_card_voided", actor_type="admin", actor_id=str(admin.id),
               target_type="report_card", target_id=str(report_card.id))
    return {"detail": "کارنامه ابطال شد"}
