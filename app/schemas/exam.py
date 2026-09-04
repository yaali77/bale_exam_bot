import uuid
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.exam import ExamStatus


class ExamCreate(BaseModel):
    title: str
    exam_code: str
    exam_date: date
    total_score: Decimal = Decimal("100")
    passing_score: Decimal
    description: str | None = None

    @field_validator("passing_score")
    @classmethod
    def passing_not_greater_than_total(cls, v, info):
        total = info.data.get("total_score")
        if total is not None and v > total:
            raise ValueError("نمره قبولی نمی‌تواند بیشتر از نمره کل باشد")
        return v


class ExamUpdate(BaseModel):
    title: str | None = None
    exam_date: date | None = None
    total_score: Decimal | None = None
    passing_score: Decimal | None = None
    description: str | None = None
    status: ExamStatus | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_scores(self):
        if self.total_score is not None and self.total_score <= 0:
            raise ValueError("نمره کل باید بیشتر از صفر باشد")

        if self.passing_score is not None and self.passing_score < 0:
            raise ValueError("نمره قبولی نمی‌تواند منفی باشد")

        if (
            self.total_score is not None
            and self.passing_score is not None
            and self.passing_score > self.total_score
        ):
            raise ValueError("نمره قبولی نمی‌تواند بیشتر از نمره کل باشد")

        return self


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    exam_code: str
    exam_date: date
    total_score: Decimal
    passing_score: Decimal
    description: str | None
    status: ExamStatus
    results_publish_date: datetime | None
    is_active: bool
    created_at: datetime
