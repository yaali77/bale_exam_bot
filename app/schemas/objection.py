import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.objection import ObjectionStatus


class ObjectionReview(BaseModel):
    status: ObjectionStatus
    resolution_note: str | None = None
    new_score: Decimal | None = None


class ObjectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    result_id: uuid.UUID
    user_id: uuid.UUID
    description: str
    status: ObjectionStatus
    resolution_note: str | None
    created_at: datetime
    resolved_at: datetime | None