"""
مدیریت ظاهر بدون نیاز به تغییر کد (بخش ۱۶ چک‌لیست).
Endpoint دریافت (GET) عمومی است تا هم بات و هم پنل (پیش از لاگین، برای رنگ صفحه ورود) بتوانند بخوانند.
Endpoint ویرایش (PATCH) فقط برای ادمین با مجوز settings است.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.appearance import AppearanceSettings
from app.schemas.appearance import AppearanceOut, AppearanceUpdate

router = APIRouter(prefix="/api/appearance", tags=["Appearance"])


def get_or_create_appearance(db: Session) -> AppearanceSettings:
    settings_row = db.query(AppearanceSettings).first()
    if not settings_row:
        settings_row = AppearanceSettings()
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


@router.get("", response_model=AppearanceOut)
def get_appearance(db: Session = Depends(get_db)):
    return get_or_create_appearance(db)


@router.patch("", response_model=AppearanceOut)
def update_appearance(
    payload: AppearanceUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("settings")),
):
    settings_row = get_or_create_appearance(db)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(settings_row, field, value)
    settings_row.updated_by_admin_id = admin.id
    db.commit()
    db.refresh(settings_row)

    log_action(db, action="appearance_updated", actor_type="admin", actor_id=str(admin.id),
               target_type="appearance_settings", target_id=str(settings_row.id), new_value=str(changes))
    return settings_row


@router.post("/reset", response_model=AppearanceOut)
def reset_appearance(db: Session = Depends(get_db), admin: Admin = Depends(require_permission("settings"))):
    """بازگردانی به تنظیمات پیش‌فرض (بخش «نسخه پیش‌فرض» چک‌لیست)"""
    settings_row = get_or_create_appearance(db)
    db.delete(settings_row)
    db.commit()
    new_settings = get_or_create_appearance(db)

    log_action(db, action="appearance_reset", actor_type="admin", actor_id=str(admin.id),
               target_type="appearance_settings", target_id=str(new_settings.id))
    return new_settings
