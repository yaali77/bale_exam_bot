import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.correction import RequestStatus


class CorrectionReview(BaseModel):
    status: RequestStatus
    admin_note: str | None = None


class CorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    field_name: str
    previous_value: str | None
    requested_value: str
    user_note: str | None
    status: RequestStatus
    admin_note: str | None
    created_at: datetime
    reviewed_at: datetime | None
