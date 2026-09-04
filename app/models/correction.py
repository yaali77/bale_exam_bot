import enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db_types import GUID
from app.database import Base


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CorrectionRequest(Base):
    """درخواست اصلاح اطلاعات کاربر"""
    __tablename__ = "correction_requests"

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        GUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    field_name = Column(
        String(50),
        nullable=False
    )

    previous_value = Column(
        String(255),
        nullable=True
    )

    requested_value = Column(
        String(255),
        nullable=False
    )

    user_note = Column(
        Text,
        nullable=True
    )

    status = Column(
        Enum(RequestStatus),
        default=RequestStatus.PENDING,
        nullable=False
    )

    admin_note = Column(
        Text,
        nullable=True
    )

    reviewed_by_admin_id = Column(
        GUID(),
        ForeignKey("admins.id"),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="correction_requests"
    )
