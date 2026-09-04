import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db_types import GUID
from app.database import Base


class ObjectionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Objection(Base):
    """اعتراض کاربر به نمره ثبت‌شده"""
    __tablename__ = "objections"

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4
    )

    result_id = Column(
        GUID(),
        ForeignKey("results.id"),
        nullable=False,
        index=True
    )

    user_id = Column(
        GUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    description = Column(
        Text,
        nullable=False
    )

    status = Column(
        Enum(ObjectionStatus),
        default=ObjectionStatus.PENDING,
        nullable=False
    )

    resolution_note = Column(
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

    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # ============================================================
    # ORM RELATIONSHIPS
    # ============================================================

    user = relationship(
        "User",
        back_populates="objections"
    )

    result = relationship(
        "Result",
        back_populates="objections"
    )

    reviewed_by_admin = relationship(
        "Admin",
        foreign_keys=[reviewed_by_admin_id],
    )
