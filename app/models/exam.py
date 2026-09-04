import enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum, Numeric, Text, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db_types import GUID
from app.database import Base


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    ENTERING_SCORES = "entering"
    READY_FOR_REVIEW = "review"
    PUBLISHED = "published"
    CLOSED = "closed"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4
    )

    title = Column(
        String(200),
        nullable=False
    )

    exam_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    exam_date = Column(
        Date,
        nullable=False
    )

    total_score = Column(
        Numeric(6, 2),
        nullable=False,
        default=100
    )

    passing_score = Column(
        Numeric(6, 2),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    status = Column(
        Enum(ExamStatus),
        default=ExamStatus.DRAFT,
        nullable=False
    )

    results_publish_date = Column(
        DateTime(timezone=True),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    results = relationship(
        "Result",
        back_populates="exam"
    )

    def __repr__(self):
        return f"<Exam {self.exam_code} - {self.status}>"
