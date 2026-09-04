"""
مانیتورینگ وضعیت سرویس‌ها (بخش ۲۲ چک‌لیست).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.bot.client import bale_client
from app.database import get_db

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


@router.get("/status")
async def system_status(db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    bot_status = "ok"
    try:
        response = await bale_client._client.get("/getMe")
        if response.status_code != 200:
            bot_status = f"error: HTTP {response.status_code}"
    except Exception as exc:
        bot_status = f"error: {exc}"

    return {
        "database": db_status,
        "bale_bot": bot_status,
    }
