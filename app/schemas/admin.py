import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.admin import AdminRole


class AdminCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: AdminRole


class AdminUpdate(BaseModel):
    full_name: str | None = None
    role: AdminRole | None = None
    is_active: bool | None = None
    new_password: str | None = None


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    role: AdminRole
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
