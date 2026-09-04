from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.feature import FeatureFlag
from app.schemas.feature import FeatureOut

router = APIRouter(prefix="/api/features", tags=["Feature Management"])


@router.get("", response_model=list[FeatureOut])
def list_features(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("view")),
):
    return (
        db.query(FeatureFlag)
        .order_by(FeatureFlag.display_name)
        .all()
    )


@router.patch("/{key}/toggle", response_model=FeatureOut)
def toggle_feature(
    key: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("settings")),
):
    feature = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.key == key)
        .first()
    )

    if not feature:
        raise HTTPException(
            status_code=404,
            detail="قابلیت یافت نشد",
        )

    previous = feature.is_enabled
    feature.is_enabled = not feature.is_enabled

    db.commit()
    db.refresh(feature)

    log_action(
        db,
        action="feature_enabled" if feature.is_enabled else "feature_disabled",
        actor_type="admin",
        actor_id=str(admin.id),
        target_type="feature",
        target_id=key,
        previous_value=str(previous),
        new_value=str(feature.is_enabled),
    )

    return feature


def is_feature_enabled(db: Session, key: str) -> bool:
    """برای استفاده در بات: بررسی فعال بودن یک قابلیت قبل از اجرای آن."""
    feature = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.key == key)
        .first()
    )

    return feature.is_enabled if feature else True
