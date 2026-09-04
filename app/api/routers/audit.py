from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database import get_db
from app.models.admin import Admin
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Log"])


@router.get("")
def list_audit_logs(
    action: str | None = None,
    target_type: str | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("report")),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
