from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_action(
    db: Session,
    action: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    previous_value: str | None = None,
    new_value: str | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuditLog:
    """ثبت یک رکورد Audit Log. برای تمام عملیات حساس فراخوانی می‌شود."""
    entry = AuditLog(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        previous_value=previous_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry
