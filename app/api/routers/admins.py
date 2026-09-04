import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission, get_current_admin
from app.core.audit import log_action
from app.core.security import hash_password
from app.database import get_db
from app.models.admin import Admin
from app.schemas.admin import AdminCreate, AdminOut, AdminUpdate

router = APIRouter(prefix="/api/admins", tags=["Admin Management"])


@router.get("", response_model=list[AdminOut])
def list_admins(db: Session = Depends(get_db), admin: Admin = Depends(require_permission("settings"))):
    return db.query(Admin).order_by(Admin.created_at.desc()).all()


@router.post("", response_model=AdminOut)
def create_admin(payload: AdminCreate, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("settings"))):
    if db.query(Admin).filter(Admin.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Ø§ÛŒÙ† Ù†Ø§Ù… Ú©Ø§Ø±Ø¨Ø±ÛŒ Ù‚Ø¨Ù„Ø§Ù‹ Ø§Ø³ØªÙØ§Ø¯Ù‡ Ø´Ø¯Ù‡ Ø§Ø³Øª")

    new_admin = Admin(
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    log_action(db, action="admin_created", actor_type="admin", actor_id=str(admin.id),
               target_type="admin", target_id=str(new_admin.id), new_value=f"role={payload.role}")
    return new_admin

@router.get("/me", response_model=AdminOut)
def get_my_profile(admin: Admin = Depends(get_current_admin)):
    return admin

@router.patch("/{admin_id}", response_model=AdminOut)
def update_admin(
    admin_id: uuid.UUID,
    payload: AdminUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("settings")),
):
    target = db.query(Admin).filter(Admin.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Ø§Ø¯Ù…ÛŒÙ† ÛŒØ§ÙØª Ù†Ø´Ø¯")

    previous_role = target.role
    changes = payload.model_dump(exclude_unset=True, exclude={"new_password"})
    for field, value in changes.items():
        setattr(target, field, value)

    if payload.new_password:
        target.hashed_password = hash_password(payload.new_password)

    db.commit()
    db.refresh(target)

    log_action(db, action="admin_updated", actor_type="admin", actor_id=str(current_admin.id),
               target_type="admin", target_id=str(target.id),
               previous_value=previous_role, new_value=str(target.role))
    return target
