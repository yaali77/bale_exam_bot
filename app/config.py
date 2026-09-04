"""
مدیریت متمرکز تنظیمات پروژه از طریق فایل .env
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Bale Bot
    BALE_BOT_TOKEN: str
    BALE_API_BASE_URL: str = "https://tapi.bale.ai"
    BALE_WEBHOOK_SECRET: str
    BALE_WEBHOOK_PATH: str = "/webhook/bale"
    PUBLIC_BASE_URL: str = ""

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # App
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SCHEDULER_ENABLED: bool = True
    ORGANIZATION_NAME: str = "آستان مقدس"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 20

    # File storage
    PDF_STORAGE_PATH: str = "/app/storage/pdf"
    EXCEL_STORAGE_PATH: str = "/app/storage/excel"
    QR_STORAGE_PATH: str = "/app/storage/qr"

    # Backup
    BACKUP_ENABLED: bool = True
    BACKUP_CRON_HOUR: int = 3
    BACKUP_RETENTION_DAYS: int = 14

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
