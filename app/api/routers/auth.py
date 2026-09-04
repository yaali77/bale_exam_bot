from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.security import verify_password, create_access_token
from app.database import get_db
from app.models.admin import Admin
from app.schemas.auth import AdminLogin, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: AdminLogin, request: Request, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == payload.username).first()

    if not admin or not verify_password(payload.password, admin.hashed_password):
        log_action(
            db, action="login_failed", actor_type="admin", actor_id=payload.username,
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")

    if not admin.is_active:
        raise HTTPException(status_code=403, detail="حساب شما غیرفعال است")

    token = create_access_token(subject=str(admin.id), extra_claims={"role": admin.role})

    log_action(
        db, action="login", actor_type="admin", actor_id=str(admin.id),
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(access_token=token)
