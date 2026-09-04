import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.broadcast_job import BroadcastJob, BroadcastJobStatus
from app.schemas.notification import BroadcastCreate, BroadcastResult, BroadcastJobOut
from app.services.notification_service import send_broadcast
from app.services.scheduler import schedule_broadcast_job, cancel_broadcast_job

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.post("/broadcast", response_model=BroadcastResult)
async def broadcast_message(
    payload: BroadcastCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("publish")),
):
    """
    ارسال یا زمان‌بندی پیام گروهی (بخش ۱۸ چک‌لیست).
    اگر schedule_at خالی باشد یا در گذشته باشد، بلافاصله ارسال می‌شود.
    در غیر این صورت، یک BroadcastJob ثبت و در APScheduler برای زمان مقرر زمان‌بندی می‌شود.
    """
    now = datetime.now(timezone.utc)
    is_immediate = payload.schedule_at is None or payload.schedule_at <= now

    job = BroadcastJob(
        message=payload.message,
        audience=payload.audience,
        exam_id=payload.exam_id,
        scheduled_at=payload.schedule_at,
        status=BroadcastJobStatus.SCHEDULED,
        created_by_admin_id=admin.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if is_immediate:
        sent, failed = await send_broadcast(db, payload.message, payload.audience, payload.exam_id)
        job.sent_count = sent
        job.failed_count = failed
        job.status = BroadcastJobStatus.SENT
        job.executed_at = now
        db.commit()

        log_action(db, action="broadcast_sent", actor_type="admin", actor_id=str(admin.id),
                   target_type="broadcast_job", target_id=str(job.id),
                   new_value=f"audience={payload.audience}, sent={sent}, failed={failed}")

        return BroadcastResult(recipients_count=sent + failed, sent_count=sent, failed_count=failed, job_id=job.id)

    schedule_broadcast_job(str(job.id), payload.schedule_at)

    log_action(db, action="broadcast_scheduled", actor_type="admin", actor_id=str(admin.id),
               target_type="broadcast_job", target_id=str(job.id),
               new_value=f"scheduled_at={payload.schedule_at.isoformat()}")

    return BroadcastResult(recipients_count=0, sent_count=0, failed_count=0, job_id=job.id)


@router.get("/jobs", response_model=list[BroadcastJobOut])
def list_broadcast_jobs(db: Session = Depends(get_db), admin: Admin = Depends(require_permission("view"))):
    return db.query(BroadcastJob).order_by(BroadcastJob.created_at.desc()).limit(100).all()


@router.post("/jobs/{job_id}/cancel", response_model=BroadcastJobOut)
def cancel_scheduled_job(job_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("publish"))):
    job = db.query(BroadcastJob).filter(BroadcastJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="پیام زمان‌بندی‌شده یافت نشد")
    if job.status != BroadcastJobStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="این پیام قابل لغو نیست (قبلاً ارسال یا لغو شده است)")

    cancel_broadcast_job(str(job.id))
    job.status = BroadcastJobStatus.CANCELLED
    db.commit()
    db.refresh(job)

    log_action(db, action="broadcast_cancelled", actor_type="admin", actor_id=str(admin.id),
               target_type="broadcast_job", target_id=str(job.id))
    return job
