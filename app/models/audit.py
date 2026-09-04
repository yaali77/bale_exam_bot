import uuid

from sqlalchemy import Column, String, DateTime, Text
from app.core.db_types import GUID
from sqlalchemy.sql import func

from app.database import Base


class AuditLog(Base):
    """
    ثبت تمام عملیات حساس سیستم: چه کسی، چه عملیاتی، روی چه چیزی،
    مقدار قبلی، مقدار جدید، چه زمانی.
    """
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    actor_type = Column(String(20), nullable=False)   # 'admin' یا 'user' یا 'system'
    actor_id = Column(String(100), nullable=True)      # شناسه عامل عملیات

    action = Column(String(100), nullable=False, index=True)   # مثل login, result_published
    target_type = Column(String(50), nullable=True)             # مثل 'result', 'user', 'exam'
    target_id = Column(String(100), nullable=True)

    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
