import enum
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Enum, BigInteger
from sqlalchemy.orm import relationship
from app.core.db_types import GUID
from sqlalchemy.sql import func

from app.database import Base


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class User(Base):
    """کاربران نهایی (شرکت‌کنندگان در آزمون) که از طریق بله ثبت‌نام می‌کنند"""
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # شناسه یکتای کاربر در بله - نباید تکراری باشد
    bale_user_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # شماره تلفن واقعی دریافت‌شده از Contact بله (نه تایپی)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)

    # کد ملی ۱۰ رقمی - یکتا؛ یک کد ملی فقط به یک حساب متصل می‌شود
    national_code = Column(String(10), unique=True, nullable=False, index=True)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)

    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
        # ============================================================
    # ORM RELATIONSHIPS
    # ============================================================

    results = relationship(
        "Result",
        back_populates="user",
    )

    objections = relationship(
        "Objection",
        back_populates="user",
    )

    correction_requests = relationship(
        "CorrectionRequest",
        back_populates="user",
    )

    report_card = relationship(
        "ReportCard",
        back_populates="user",
        uselist=False,
    )

    def __repr__(self):
        return f"<User {self.national_code} - {self.status}>"
