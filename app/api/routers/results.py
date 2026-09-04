import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.models.admin import has_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.exam import Exam
from app.models.result import Result, ResultHistory, ResultStatus
from app.models.user import User
from app.schemas.result import ResultCreate, ResultOut, ResultUpdate, ResultHistoryOut
from app.services.notification_service import notify_result_published

router = APIRouter(prefix="/api/results", tags=["Results"])


@router.get("", response_model=list[ResultOut])
def list_results(
    exam_id: uuid.UUID | None = None,
    status: ResultStatus | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("view")),
):
    query = db.query(Result)
    if exam_id:
        query = query.filter(Result.exam_id == exam_id)
    if status:
        query = query.filter(Result.status == status)
    return query.order_by(Result.recorded_at.desc()).limit(500).all()


@router.post("", response_model=ResultOut)
def create_result(payload: ResultCreate, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("create"))):
    user = db.query(User).filter(User.national_code == payload.user_national_code).first()
    if not user:
        raise HTTPException(status_code=404, detail="ÃšÂ©Ã˜Â§Ã˜Â±Ã˜Â¨Ã˜Â±Ã›Å’ Ã˜Â¨Ã˜Â§ Ã˜Â§Ã›Å’Ã™â€  ÃšÂ©Ã˜Â¯ Ã™â€¦Ã™â€žÃ›Å’ Ã›Å’Ã˜Â§Ã™ÂÃ˜Âª Ã™â€ Ã˜Â´Ã˜Â¯")

    exam = db.query(Exam).filter(Exam.id == payload.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Ã˜Â¢Ã˜Â²Ã™â€¦Ã™Ë†Ã™â€  Ã›Å’Ã˜Â§Ã™ÂÃ˜Âª Ã™â€ Ã˜Â´Ã˜Â¯")

    if db.query(Result).filter(Result.user_id == user.id, Result.exam_id == exam.id).first():
        raise HTTPException(status_code=400, detail="Ã™â€ Ã™â€¦Ã˜Â±Ã™â€¡ Ã˜Â§Ã›Å’Ã™â€  ÃšÂ©Ã˜Â§Ã˜Â±Ã˜Â¨Ã˜Â± Ã˜Â¨Ã˜Â±Ã˜Â§Ã›Å’ Ã˜Â§Ã›Å’Ã™â€  Ã˜Â¢Ã˜Â²Ã™â€¦Ã™Ë†Ã™â€  Ã™â€šÃ˜Â¨Ã™â€žÃ˜Â§Ã™â€¹ Ã˜Â«Ã˜Â¨Ã˜Âª Ã˜Â´Ã˜Â¯Ã™â€¡ Ã˜Â§Ã˜Â³Ã˜Âª")

    if payload.score < 0 or payload.score > exam.total_score:
        raise HTTPException(status_code=400, detail=f"Ã™â€ Ã™â€¦Ã˜Â±Ã™â€¡ Ã˜Â¨Ã˜Â§Ã›Å’Ã˜Â¯ Ã˜Â¨Ã›Å’Ã™â€  Ã›Â° Ã˜ÂªÃ˜Â§ {exam.total_score} Ã˜Â¨Ã˜Â§Ã˜Â´Ã˜Â¯")

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=payload.score,
        is_passed=payload.score >= exam.passing_score,
        status=ResultStatus.RECORDED,
        recorded_by_admin_id=admin.id,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    log_action(db, action="result_created", actor_type="admin", actor_id=str(admin.id),
               target_type="result", target_id=str(result.id), new_value=str(payload.score))
    return result


@router.patch("/{result_id}", response_model=ResultOut)
def update_result(
    result_id: uuid.UUID,
    payload: ResultUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("edit")),
):
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Ã™â€ Ã™â€¦Ã˜Â±Ã™â€¡ Ã›Å’Ã˜Â§Ã™ÂÃ˜Âª Ã™â€ Ã˜Â´Ã˜Â¯")

    history = ResultHistory(
        result_id=result.id,
        previous_score=result.score,
        previous_status=result.status,
        changed_by_admin_id=admin.id,
        reason=payload.change_reason,
    )

    if payload.score is not None:
        exam = db.query(Exam).filter(Exam.id == result.exam_id).first()
        if payload.score < 0 or payload.score > exam.total_score:
            raise HTTPException(status_code=400, detail=f"Ã™â€ Ã™â€¦Ã˜Â±Ã™â€¡ Ã˜Â¨Ã˜Â§Ã›Å’Ã˜Â¯ Ã˜Â¨Ã›Å’Ã™â€  Ã›Â° Ã˜ÂªÃ˜Â§ {exam.total_score} Ã˜Â¨Ã˜Â§Ã˜Â´Ã˜Â¯")
        result.score = payload.score
        result.is_passed = payload.score >= exam.passing_score
        result.notification_sent = False  # Ã˜Â§ÃšÂ¯Ã˜Â± Ã™â€ Ã™â€¦Ã˜Â±Ã™â€¡ Ã˜ÂªÃ˜ÂºÃ›Å’Ã›Å’Ã˜Â± ÃšÂ©Ã™â€ Ã˜Â¯ Ã™Ë† Ã˜Â¯Ã™Ë†Ã˜Â¨Ã˜Â§Ã˜Â±Ã™â€¡ Ã™â€¦Ã™â€ Ã˜ÂªÃ˜Â´Ã˜Â± Ã˜Â´Ã™Ë†Ã˜Â¯Ã˜Å’ Ã˜Â¨Ã˜Â§Ã›Å’Ã˜Â¯ Ã˜Â¯Ã™Ë†Ã˜Â¨Ã˜Â§Ã˜Â±Ã™â€¡ Ã˜Â§Ã˜Â·Ã™â€žÃ˜Â§Ã˜Â¹Ã¢â‚¬Å’Ã˜Â±Ã˜Â³Ã˜Â§Ã™â€ Ã›Å’ Ã˜Â´Ã™Ë†Ã˜Â¯

    if payload.status is not None:
        if (
            payload.status == ResultStatus.PUBLISHED
            and not has_permission(admin.role, "publish")
        ):
            raise HTTPException(
                status_code=403,
                detail="Ø´Ù…Ø§ Ù…Ø¬ÙˆØ² Ø§Ù†ØªØ´Ø§Ø± Ù†ØªÛŒØ¬Ù‡ Ø±Ø§ Ù†Ø¯Ø§Ø±ÛŒØ¯",
            )

        result.status = payload.status

        if payload.status == ResultStatus.PUBLISHED:
            result.published_at = datetime.now(timezone.utc)
            result.published_by_admin_id = admin.id

    result.change_reason = payload.change_reason

    history.new_score = result.score
    history.new_status = result.status
    db.add(history)
    db.commit()
    db.refresh(result)

    log_action(db, action="result_updated", actor_type="admin", actor_id=str(admin.id),
               target_type="result", target_id=str(result.id),
               previous_value=str(history.previous_score), new_value=str(result.score))
    return result


@router.post("/{result_id}/publish", response_model=ResultOut)
async def publish_result(
    result_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("publish")),
):
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Ù†Ù…Ø±Ù‡ ÛŒØ§ÙØª Ù†Ø´Ø¯")

    history = ResultHistory(
        result_id=result.id,
        previous_score=result.score,
        new_score=result.score,
        previous_status=result.status.value,
        new_status=ResultStatus.PUBLISHED.value,
        changed_by_admin_id=admin.id,
        reason="Ø§Ù†ØªØ´Ø§Ø± Ù†ØªÛŒØ¬Ù‡",
    )

    result.status = ResultStatus.PUBLISHED
    result.published_at = datetime.now(timezone.utc)
    result.published_by_admin_id = admin.id
    result.notification_sent = False

    db.add(history)
    db.commit()
    db.refresh(result)

    log_action(
        db,
        action="result_published",
        actor_type="admin",
        actor_id=str(admin.id),
        target_type="result",
        target_id=str(result.id),
    )

    background_tasks.add_task(notify_result_published, db, result)

    return result


@router.post("/publish-bulk")
async def publish_bulk(
    exam_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("publish")),
):
    """?????? ????? ???? ????? ?? ?????"""

    results = (
        db.query(Result)
        .filter(
            Result.exam_id == exam_id,
            Result.status != ResultStatus.PUBLISHED,
        )
        .all()
    )

    now = datetime.now(timezone.utc)

    for result in results:
        history = ResultHistory(
            result_id=result.id,
            previous_score=result.score,
            new_score=result.score,
            previous_status=result.status.value,
            new_status=ResultStatus.PUBLISHED.value,
            changed_by_admin_id=admin.id,
            reason="?????? ????? ?????",
        )

        result.status = ResultStatus.PUBLISHED
        result.published_at = now
        result.published_by_admin_id = admin.id
        result.notification_sent = False

        db.add(history)

        background_tasks.add_task(
            notify_result_published,
            db,
            result,
        )

    db.commit()

    log_action(
        db,
        action="results_bulk_published",
        actor_type="admin",
        actor_id=str(admin.id),
        target_type="exam",
        target_id=str(exam_id),
        new_value=f"count={len(results)}",
    )

    return {"published_count": len(results)}


@router.post("/{result_id}/unpublish", response_model=ResultOut)
def unpublish_result(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("publish")),
):
    result = db.query(Result).filter(Result.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Ù†Ù…Ø±Ù‡ ÛŒØ§ÙØª Ù†Ø´Ø¯")

    history = ResultHistory(
        result_id=result.id,
        previous_score=result.score,
        new_score=result.score,
        previous_status=result.status.value,
        new_status=ResultStatus.REVIEWED.value,
        changed_by_admin_id=admin.id,
        reason="Ù„ØºÙˆ Ø§Ù†ØªØ´Ø§Ø± Ù†ØªÛŒØ¬Ù‡",
    )

    result.status = ResultStatus.REVIEWED
    result.published_at = None
    result.published_by_admin_id = None
    result.notification_sent = False

    db.add(history)
    db.commit()
    db.refresh(result)

    log_action(
        db,
        action="result_unpublished",
        actor_type="admin",
        actor_id=str(admin.id),
        target_type="result",
        target_id=str(result.id),
    )

    return result


@router.post("/{result_id}/void", response_model=ResultOut)
def void_result(
    result_id: uuid.UUID,
    reason: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("delete")),
):
    result = db.query(Result).filter(Result.id == result_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Ù†Ù…Ø±Ù‡ ÛŒØ§ÙØª Ù†Ø´Ø¯")

    history = ResultHistory(
        result_id=result.id,
        previous_score=result.score,
        new_score=result.score,
        previous_status=result.status.value,
        new_status=ResultStatus.VOIDED.value,
        changed_by_admin_id=admin.id,
        reason=reason,
    )

    result.status = ResultStatus.VOIDED
    result.change_reason = reason
    result.published_at = None
    result.published_by_admin_id = None
    result.notification_sent = False

    db.add(history)
    db.commit()
    db.refresh(result)

    log_action(
        db,
        action="result_voided",
        actor_type="admin",
        actor_id=str(admin.id),
        target_type="result",
        target_id=str(result.id),
        new_value=reason,
    )

    return result


@router.get("/{result_id}/history", response_model=list[ResultHistoryOut])
def get_result_history(result_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("view"))):
    return db.query(ResultHistory).filter(ResultHistory.result_id == result_id).order_by(ResultHistory.changed_at.desc()).all()
