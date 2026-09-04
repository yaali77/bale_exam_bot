"""
پیگیری وضعیت پیام‌های زمان‌بندی‌شده و ارسال‌شده (بخش ۱۸ چک‌لیست: زمان‌بندی پیام).
"""
import enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum, Text, Integer
from sqlalchemy.sql import func

from app.core.db_types import GUID
from app.database import Base


class BroadcastJobStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    message = Column(Text, nullable=False)
    audience = Column(String(20), nullable=False)
    exam_id = Column(GUID(), nullable=True)

    status = Column(Enum(BroadcastJobStatus), default=BroadcastJobStatus.SCHEDULED, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # خالی یعنی ارسال فوری

    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_by_admin_id = Column(GUID(), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)
