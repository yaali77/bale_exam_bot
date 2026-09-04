import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bale_user_id: int
    phone_number: str
    national_code: str
    first_name: str | None
    last_name: str | None
    status: UserStatus
    registered_at: datetime


class UserStatusUpdate(BaseModel):
    status: UserStatus
