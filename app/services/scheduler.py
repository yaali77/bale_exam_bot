"""
راه‌اندازی APScheduler برای دو کارکرد:
1. اجرای پیام‌های زمان‌بندی‌شده (بخش ۱۸ چک‌لیست)
2. Backup خودکار روزانه دیتابیس (بخش ۲۱ چک‌لیست)

Scheduler در پردازه اصلی FastAPI اجرا می‌شود (in-process). برای استقرارهای با چند Replica از
backend، باید این بخش به یک Worker جداگانه (مثل APScheduler با Job Store دیتابیسی، یا Celery Beat) منتقل شود.
"""
import asyncio
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.core.logging import get_logger
from app.database import SessionLocal
from app.models.broadcast_job import BroadcastJob, BroadcastJobStatus
from app.services.backup_service import run_database_backup
from app.services.notification_service import send_broadcast

logger = get_logger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")


async def _execute_broadcast_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(BroadcastJob).filter(BroadcastJob.id == job_id).first()
        if not job or job.status != BroadcastJobStatus.SCHEDULED:
            return

        sent, failed = await send_broadcast(db, job.message, job.audience, job.exam_id)
        job.sent_count = sent
        job.failed_count = failed
        job.status = BroadcastJobStatus.SENT
        job.executed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Broadcast job %s executed: sent=%s failed=%s", job_id, sent, failed)
    except Exception:
        logger.exception("Broadcast job %s failed", job_id)
        job = db.query(BroadcastJob).filter(BroadcastJob.id == job_id).first()
        if job:
            job.status = BroadcastJobStatus.FAILED
            db.commit()
    finally:
        db.close()


def schedule_broadcast_job(job_id: str, run_at: datetime):
    """یک Job زمان‌بندی‌شده در APScheduler ثبت می‌کند"""
    scheduler.add_job(
        _execute_broadcast_job,
        trigger="date",
        run_date=run_at,
        args=[job_id],
        id=f"broadcast_{job_id}",
        replace_existing=True,
        misfire_grace_time=3600,
    )


def cancel_broadcast_job(job_id: str):
    try:
        scheduler.remove_job(f"broadcast_{job_id}")
    except Exception:
        pass  # Job از قبل اجرا شده یا وجود ندارد


async def _run_backup_job():
    logger.info("Starting scheduled database backup")
    try:
        await asyncio.to_thread(run_database_backup)
        logger.info("Scheduled database backup completed successfully")
    except Exception:
        logger.exception("Scheduled database backup failed")


def init_scheduler():
    """راه‌اندازی Scheduler و بازیابی Jobهای زمان‌بندی‌شده‌ای که هنوز اجرا نشده‌اند (پس از راه‌اندازی مجدد سرویس)"""
    if settings.BACKUP_ENABLED:
        scheduler.add_job(
            _run_backup_job,
            trigger=CronTrigger(hour=settings.BACKUP_CRON_HOUR, minute=0),
            id="daily_backup",
            replace_existing=True,
        )
        logger.info("Daily backup job scheduled for %02d:00 UTC", settings.BACKUP_CRON_HOUR)

    # بازیابی پیام‌های زمان‌بندی‌شده که هنوز موعدشان نرسیده (مثلاً پس از ری‌استارت سرویس)
    db = SessionLocal()
    try:
        pending_jobs = db.query(BroadcastJob).filter(BroadcastJob.status == BroadcastJobStatus.SCHEDULED).all()
        now = datetime.now(timezone.utc)
        for job in pending_jobs:
            if job.scheduled_at and job.scheduled_at > now:
                schedule_broadcast_job(str(job.id), job.scheduled_at)
            elif job.scheduled_at:
                # موعد گذشته و سرویس خاموش بوده: بلافاصله اجرا کن
                schedule_broadcast_job(str(job.id), now)
    finally:
        db.close()

    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
