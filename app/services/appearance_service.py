"""دسترسی سریع به تنظیمات ظاهری از هرجای بات، بدون تکرار کوئری در هر هندلر"""
from sqlalchemy.orm import Session

from app.models.appearance import AppearanceSettings


def get_appearance(db: Session) -> AppearanceSettings:
    settings_row = db.query(AppearanceSettings).first()
    if not settings_row:
        settings_row = AppearanceSettings()
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row
