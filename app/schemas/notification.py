from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict
import uuid


class BroadcastAudience(str, Enum):
    ALL = "all"                      # ارسال به همه
    EXAM_PARTICIPANTS = "exam"       # شرکت‌کنندگان یک آزمون خاص
    PASSED = "passed"                # قبول‌شدگان
    FAILED = "failed"                # مردودشدگان


class BroadcastCreate(BaseModel):
    message: str
    audience: BroadcastAudience
    exam_id: uuid.UUID | None = None
    schedule_at: datetime | None = None


class BroadcastResult(BaseModel):
    recipients_count: int
    sent_count: int
    failed_count: int
    job_id: uuid.UUID


class BroadcastJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message: str
    audience: str
    status: str
    scheduled_at: datetime | None
    sent_count: int
    failed_count: int
    created_at: datetime
    executed_at: datetime | None
