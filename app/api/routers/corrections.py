import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.correction import CorrectionRequest, RequestStatus
from app.models.user import User
from app.schemas.correction import CorrectionOut, CorrectionReview

router = APIRouter(prefix="/api/corrections", tags=["Correction Requests"])

ALLOWED_FIELDS = {"first_name", "last_name", "phone_number"}  # کد ملی هرگز از این مسیر قابل تغییر نیست


@router.get("", response_model=list[CorrectionOut])
def list_correction_requests(
    status: RequestStatus | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("view")),
):
    query = db.query(CorrectionRequest)
    if status:
        query = query.filter(CorrectionRequest.status == status)
    return query.order_by(CorrectionRequest.created_at.desc()).all()


@router.post("/{request_id}/review", response_model=CorrectionOut)
def review_correction_request(
    request_id: uuid.UUID,
    payload: CorrectionReview,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("edit")),
):
    correction = db.query(CorrectionRequest).filter(CorrectionRequest.id == request_id).first()
    if not correction:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    correction.status = payload.status
    correction.admin_note = payload.admin_note
    correction.reviewed_by_admin_id = admin.id
    correction.reviewed_at = datetime.now(timezone.utc)

    if payload.status == RequestStatus.APPROVED:
        if correction.field_name not in ALLOWED_FIELDS:
            raise HTTPException(status_code=400, detail="این فیلد از طریق درخواست اصلاح قابل تغییر نیست")
        user = db.query(User).filter(User.id == correction.user_id).first()
        setattr(user, correction.field_name, correction.requested_value)

    db.commit()
    db.refresh(correction)

    log_action(db, action="correction_reviewed", actor_type="admin", actor_id=str(admin.id),
               target_type="correction_request", target_id=str(correction.id),
               previous_value=correction.previous_value, new_value=correction.requested_value)
    return correction
