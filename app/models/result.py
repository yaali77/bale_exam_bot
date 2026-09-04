import enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum, Numeric, Text, ForeignKey, Boolean
from app.core.db_types import GUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ResultStatus(str, enum.Enum):
    RECORDED = "recorded"      # نمره ثبت‌شده
    REVIEWED = "reviewed"      # نمره بررسی‌شده
    PUBLISHED = "published"    # نمره منتشرشده
    VOIDED = "voided"          # نمره ابطال‌شده


class Result(Base):
    """نتیجه یک کاربر در یک آزمون"""
    __tablename__ = "results"

    __table_args__ = (
        # در مرحله Migration اضافه خواهد شد:
        # UniqueConstraint("user_id", "exam_id", name="uq_results_user_exam"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        GUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    exam_id = Column(
        GUID(),
        ForeignKey("exams.id"),
        nullable=False,
        index=True,
    )

    score = Column(
        Numeric(6, 2),
        nullable=False,
    )

    is_passed = Column(
        Boolean,
        nullable=True,
    )

    status = Column(
        Enum(ResultStatus),
        default=ResultStatus.RECORDED,
        nullable=False,
    )

    recorded_by_admin_id = Column(
        GUID(),
        ForeignKey("admins.id"),
        nullable=True,
    )

    published_by_admin_id = Column(
        GUID(),
        ForeignKey("admins.id"),
        nullable=True,
    )

    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    change_reason = Column(
        Text,
        nullable=True,
    )

    notification_sent = Column(
        Boolean,
        default=False,
    )

    # ============================================================
    # ORM RELATIONSHIPS
    # ============================================================

    user = relationship(
        "User",
        back_populates="results",
    )

    exam = relationship(
        "Exam",
        back_populates="results",
    )

    recorded_by_admin = relationship(
        "Admin",
        foreign_keys=[recorded_by_admin_id],
        back_populates="recorded_results",
    )

    published_by_admin = relationship(
        "Admin",
        foreign_keys=[published_by_admin_id],
        back_populates="published_results",
    )

    history = relationship(
        "ResultHistory",
        back_populates="result",
    )

    objections = relationship(
        "Objection",
        back_populates="result",
    )


class ResultHistory(Base):
    """تاریخچه تغییرات نمره برای شفافیت و Audit"""
    __tablename__ = "result_history"

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )

    result_id = Column(
        GUID(),
        ForeignKey("results.id"),
        nullable=False,
        index=True,
    )

    previous_score = Column(
        Numeric(6, 2),
        nullable=True,
    )

    new_score = Column(
        Numeric(6, 2),
        nullable=True,
    )

    previous_status = Column(
        String(20),
        nullable=True,
    )

    new_status = Column(
        String(20),
        nullable=True,
    )

    changed_by_admin_id = Column(
        GUID(),
        ForeignKey("admins.id"),
        nullable=True,
    )

    reason = Column(
        Text,
        nullable=True,
    )

    changed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # ============================================================
    # ORM RELATIONSHIPS
    # ============================================================

    result = relationship(
        "Result",
        back_populates="history",
    )

    changed_by_admin = relationship(
        "Admin",
        foreign_keys=[changed_by_admin_id],
        back_populates="result_histories",
    )
