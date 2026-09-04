from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.deps import require_permission
from app.models.admin import Admin
from app.services.backup_service import list_backups, run_database_backup

router = APIRouter(prefix="/api/backups", tags=["Backup"])


@router.get("")
def get_backup_status(admin: Admin = Depends(require_permission("report"))):
    """گزارش وضعیت Backup: لیست نسخه‌های موجود با تاریخ و حجم (بخش ۲۱ چک‌لیست)"""
    return {"backups": list_backups()}


@router.post("/run-now")
def trigger_manual_backup(background_tasks: BackgroundTasks, admin: Admin = Depends(require_permission("settings"))):
    """اجرای دستی Backup خارج از زمان‌بندی روزانه"""
    background_tasks.add_task(run_database_backup)
    return {"detail": "Backup در پس‌زمینه شروع شد"}
