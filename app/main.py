import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.database import Base, engine, SessionLocal
# Ø§ÛŒÙ…Ù¾ÙˆØ±Øª ØªÙ…Ø§Ù… Ù…Ø¯Ù„â€ŒÙ‡Ø§ Ø¶Ø±ÙˆØ±ÛŒ Ø§Ø³Øª ØªØ§ SQLAlchemy Ù¾ÛŒØ´ Ø§Ø² create_all() Ø¢Ù†â€ŒÙ‡Ø§ Ø±Ø§ Ø¯Ø± Base.metadata Ø«Ø¨Øª Ú©Ù†Ø¯
from app import models  # noqa: F401
from app.models.feature import FeatureFlag, DEFAULT_FEATURES
from app.services.scheduler import init_scheduler, shutdown_scheduler

from app.bot.webhook import router as bale_webhook_router
from app.api.routers.auth import router as auth_router
from app.api.routers.users import router as users_router
from app.api.routers.features import router as features_router
from app.api.routers.exams import router as exams_router
from app.api.routers.results import router as results_router
from app.api.routers.excel import router as excel_router
from app.api.routers.reportcard import router as reportcard_router
from app.api.routers.corrections import router as corrections_router
from app.api.routers.objections import router as objections_router
from app.api.routers.notifications import router as notifications_router
from app.api.routers.admins import router as admins_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.audit import router as audit_router
from app.api.routers.monitoring import router as monitoring_router
from app.api.routers.appearance import router as appearance_router
from app.api.routers.backup import router as backup_router

setup_logging()
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


def seed_default_features():
    """Ø§Ø·Ù…ÛŒÙ†Ø§Ù† Ø§Ø² ÙˆØ¬ÙˆØ¯ Ø±Ú©ÙˆØ±Ø¯Ù‡Ø§ÛŒ Ù¾ÛŒØ´â€ŒÙØ±Ø¶ Feature Flag Ø¯Ø± Ø§ÙˆÙ„ÛŒÙ† Ø§Ø¬Ø±Ø§"""
    db = SessionLocal()
    try:
        for key, display_name in DEFAULT_FEATURES:
            if not db.query(FeatureFlag).filter(FeatureFlag.key == key).first():
                db.add(FeatureFlag(key=key, display_name=display_name, is_enabled=True))
        db.commit()
    finally:
        db.close()


def seed_default_appearance():
    """Ø§Ø·Ù…ÛŒÙ†Ø§Ù† Ø§Ø² ÙˆØ¬ÙˆØ¯ Ø¯Ù‚ÛŒÙ‚Ø§Ù‹ ÛŒÚ© Ø±Ú©ÙˆØ±Ø¯ ØªÙ†Ø¸ÛŒÙ…Ø§Øª Ø¸Ø§Ù‡Ø±ÛŒ (Singleton) Ø¯Ø± Ø§ÙˆÙ„ÛŒÙ† Ø§Ø¬Ø±Ø§"""
    from app.models.appearance import AppearanceSettings

    db = SessionLocal()
    try:
        if not db.query(AppearanceSettings).first():
            db.add(AppearanceSettings())
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ø§ÛŒØ¬Ø§Ø¯ Ø¬Ø¯Ø§ÙˆÙ„ (Ø¯Ø± Production ØªÙˆØµÛŒÙ‡ Ù…ÛŒâ€ŒØ´ÙˆØ¯ Ø§Ø² Alembic Migration Ø§Ø³ØªÙØ§Ø¯Ù‡ Ø´ÙˆØ¯)
    Base.metadata.create_all(bind=engine)
    seed_default_features()
    seed_default_appearance()

    if settings.SCHEDULER_ENABLED:
        try:
            init_scheduler()
        except Exception:
            logger.exception(
                "Scheduler failed to start; scheduled backups and broadcasts will not run"
            )
    else:
        logger.info("Scheduler is disabled")

    logger.info(
        "Application startup complete. Environment=%s",
        settings.ENVIRONMENT,
    )
    yield

    if settings.SCHEDULER_ENABLED:
        shutdown_scheduler()

    logger.info("Application shutting down")


app = FastAPI(
    title=f"{settings.ORGANIZATION_NAME} - Ø³Ø§Ù…Ø§Ù†Ù‡ Ø§Ø¹Ù„Ø§Ù… Ù†ØªØ§ÛŒØ¬ Ø¢Ø²Ù…ÙˆÙ†",
    description="Ø¨Ú©â€ŒØ§Ù†Ø¯ Ø¨Ø§Øª Ø¨Ù„Ù‡ Ø¨Ø±Ø§ÛŒ Ø§Ø¹Ù„Ø§Ù… Ù†ØªØ§ÛŒØ¬ Ø¢Ø²Ù…ÙˆÙ† Ø¨Ù‡ Ù‡Ù…Ø±Ø§Ù‡ Ù¾Ù†Ù„ Ù…Ø¯ÛŒØ±ÛŒØª",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.PUBLIC_BASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ø±ÙˆØªØ±Ù‡Ø§
app.include_router(bale_webhook_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(features_router)
app.include_router(exams_router)
app.include_router(results_router)
app.include_router(excel_router)
app.include_router(reportcard_router)
app.include_router(corrections_router)
app.include_router(objections_router)
app.include_router(notifications_router)
app.include_router(admins_router)
app.include_router(dashboard_router)
app.include_router(audit_router)
app.include_router(monitoring_router)
app.include_router(appearance_router)
app.include_router(backup_router)

try:
    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.QR_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.EXCEL_STORAGE_PATH, exist_ok=True)
    # Ø³Ø±Ùˆ Ù…Ø³ØªÙ‚ÛŒÙ… ÙØ§ÛŒÙ„â€ŒÙ‡Ø§ÛŒ PDF/QR Ø§Ø² Ø·Ø±ÛŒÙ‚ Nginx Ù†ÛŒØ² Ø¯Ø± nginx.conf ØªÙ†Ø¸ÛŒÙ… Ø´Ø¯Ù‡Ø› Ø§ÛŒÙ† Ø®Ø· Ø¨Ø±Ø§ÛŒ Ø¯Ø³ØªØ±Ø³ÛŒ Ù…Ø³ØªÙ‚ÛŒÙ… Ø¨Ù‡ Ø¨Ú©â€ŒØ§Ù†Ø¯ Ø§Ø³Øª
    app.mount("/storage", StaticFiles(directory=os.path.dirname(settings.PDF_STORAGE_PATH)), name="storage")
except OSError:
    logger.warning("Could not create/mount storage directories (likely running outside Docker). Skipping static mount.")


@app.get("/health", tags=["System"])
def health_check():
    """Ø¨Ø±Ø±Ø³ÛŒ Ø³Ù„Ø§Ù…Øª Ø³Ø±ÙˆÛŒØ³ - Ø¨Ø±Ø§ÛŒ Docker Healthcheck Ùˆ Monitoring"""
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["System"])
def root():
    return {"message": f"{settings.ORGANIZATION_NAME} - Ø³Ø§Ù…Ø§Ù†Ù‡ Ø§Ø¹Ù„Ø§Ù… Ù†ØªØ§ÛŒØ¬ Ø¢Ø²Ù…ÙˆÙ† ÙØ¹Ø§Ù„ Ø§Ø³Øª"}
