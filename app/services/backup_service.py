"""
پشتیبان‌گیری خودکار روزانه از دیتابیس با pg_dump + نگهداری چند نسخه + پاکسازی فایل‌های قدیمی
(بخش ۲۱ چک‌لیست).
"""
import os
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

BACKUP_DIR = "/backups"


def _parse_db_url():
    """استخراج پارامترهای اتصال از DATABASE_URL برای استفاده در pg_dump"""
    parsed = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg2", "postgresql"))
    return {
        "host": parsed.hostname,
        "port": str(parsed.port or 5432),
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip("/"),
    }


def run_database_backup() -> str | None:
    """
    اجرای pg_dump و ذخیره فایل فشرده. فایل‌های قدیمی‌تر از BACKUP_RETENTION_DAYS پاک می‌شوند.
    این تابع Sync است چون subprocess.run بلاک‌کننده است؛ در Scheduler با asyncio.to_thread صدا زده می‌شود.
    """
    if not settings.DATABASE_URL.startswith("postgresql"):
        logger.warning("Backup skipped: DATABASE_URL is not PostgreSQL (احتمالاً محیط تست با SQLite است)")
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    db_params = _parse_db_url()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.sql.gz")

    env = os.environ.copy()
    if db_params["password"]:
        env["PGPASSWORD"] = db_params["password"]

    dump_cmd = [
        "pg_dump",
        "-h", db_params["host"],
        "-p", db_params["port"],
        "-U", db_params["user"],
        "-d", db_params["dbname"],
        "--no-owner", "--no-privileges",
    ]

    with open(file_path, "wb") as f:
        dump_proc = subprocess.run(dump_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        gzip_proc = subprocess.run(["gzip"], input=dump_proc.stdout, stdout=f, stderr=subprocess.PIPE, check=True)

    logger.info("Database backup created at %s", file_path)
    _cleanup_old_backups()
    return file_path


def _cleanup_old_backups():
    """حذف فایل‌های Backup قدیمی‌تر از دوره نگهداری تنظیم‌شده"""
    if not os.path.isdir(BACKUP_DIR):
        return

    cutoff = datetime.now(timezone.utc).timestamp() - (settings.BACKUP_RETENTION_DAYS * 86400)
    for filename in os.listdir(BACKUP_DIR):
        file_path = os.path.join(BACKUP_DIR, filename)
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
            os.remove(file_path)
            logger.info("Removed old backup: %s", filename)


def list_backups() -> list[dict]:
    """لیست فایل‌های Backup موجود، برای نمایش در پنل مدیریت (گزارش وضعیت Backup)"""
    if not os.path.isdir(BACKUP_DIR):
        return []
    items = []
    for filename in sorted(os.listdir(BACKUP_DIR), reverse=True):
        file_path = os.path.join(BACKUP_DIR, filename)
        if os.path.isfile(file_path):
            items.append({
                "filename": filename,
                "size_bytes": os.path.getsize(file_path),
                "created_at": datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc).isoformat(),
            })
    return items
