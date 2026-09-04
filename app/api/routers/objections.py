import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.exam import Exam
from app.models.objection import Objection, ObjectionStatus
from app.models.result import Result, ResultHistory
from app.schemas.objection import ObjectionOut, ObjectionReview

router = APIRouter(prefix="/api/objections", tags=["Objections"])


@router.get("", response_model=list[ObjectionOut])
def list_objections(
    status: ObjectionStatus | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("view")),
):
    query = db.query(Objection)
    if status:
        query = query.filter(Objection.status == status)
    return query.order_by(Objection.created_at.desc()).all()


@router.post("/{objection_id}/review", response_model=ObjectionOut)
def review_objection(
    objection_id: uuid.UUID,
    payload: ObjectionReview,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("edit")),
):
    objection = db.query(Objection).filter(Objection.id == objection_id).first()
    if not objection:
        raise HTTPException(status_code=404, detail="اعتراض یافت نشد")

    objection.status = payload.status
    objection.resolution_note = payload.resolution_note
    objection.reviewed_by_admin_id = admin.id
    objection.resolved_at = datetime.now(timezone.utc)

    if payload.status == ObjectionStatus.APPROVED and payload.new_score is not None:
        result = db.query(Result).filter(Result.id == objection.result_id).first()
        exam = db.query(Exam).filter(Exam.id == result.exam_id).first()
        new_score = Decimal(payload.new_score)

        if new_score < 0 or new_score > exam.total_score:
            raise HTTPException(status_code=400, detail=f"نمره باید بین ۰ تا {exam.total_score} باشد")

        history = ResultHistory(
            result_id=result.id, previous_score=result.score, previous_status=result.status,
            changed_by_admin_id=admin.id, reason=f"اصلاح بر اساس اعتراض #{objection.id}",
        )
        result.score = new_score
        result.is_passed = new_score >= exam.passing_score
        result.notification_sent = False
        history.new_score = result.score
        history.new_status = result.status
        db.add(history)

    db.commit()
    db.refresh(objection)

    log_action(db, action="objection_reviewed", actor_type="admin", actor_id=str(admin.id),
               target_type="objection", target_id=str(objection.id), new_value=payload.status)
    return objection
