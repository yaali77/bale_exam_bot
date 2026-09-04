import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.result import ResultStatus


class ResultCreate(BaseModel):
    user_national_code: str
    exam_id: uuid.UUID
    score: Decimal


class ResultUpdate(BaseModel):
    score: Decimal | None = None
    status: ResultStatus | None = None
    change_reason: str


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    exam_id: uuid.UUID
    score: Decimal
    is_passed: bool | None = None
    status: ResultStatus
    recorded_at: datetime
    published_at: datetime | None


class ResultHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    previous_score: Decimal | None
    new_score: Decimal | None
    previous_status: str | None
    new_status: str | None
    reason: str | None
    changed_at: datetime


class ExcelImportRowError(BaseModel):
    row_number: int
    national_code: str | None = None
    error: str


class ExcelImportResult(BaseModel):
    total_rows: int
    success_count: int
    error_count: int
    errors: list[ExcelImportRowError]
