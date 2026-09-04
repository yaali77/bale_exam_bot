import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db_types import GUID
from app.database import Base


class ReportCard(Base):
    """
    کارنامه تجمیعی یک کاربر، شامل اطلاعات آزمون‌های منتشرشده،
    کد اعتبارسنجی و QR.
    """

    __tablename__ = "report_cards"

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        GUID(),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True
    )

    report_number = Column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )

    verification_code = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )

    pdf_path = Column(
        String(500),
        nullable=True
    )

    qr_path = Column(
        String(500),
        nullable=True
    )

    is_valid = Column(
        Boolean,
        default=True,
        nullable=False
    )

    issued_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="report_card"
    )
