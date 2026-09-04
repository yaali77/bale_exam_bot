import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.schemas.user import UserOut, UserStatusUpdate

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=list[UserOut])
def list_users(
    search: str | None = Query(default=None, description="جستجو بر اساس نام، کد ملی یا شماره تلفن"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("view")),
):
    query = db.query(User)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (User.national_code.ilike(like))
            | (User.phone_number.ilike(like))
            | (User.first_name.ilike(like))
            | (User.last_name.ilike(like))
        )
    return query.order_by(User.registered_at.desc()).limit(200).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("view"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return user


@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("edit")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")

    previous_status = user.status
    user.status = payload.status
    db.commit()
    db.refresh(user)

    log_action(
        db, action="user_status_changed", actor_type="admin", actor_id=str(admin.id),
        target_type="user", target_id=str(user.id),
        previous_value=previous_status, new_value=payload.status,
    )
    return user
