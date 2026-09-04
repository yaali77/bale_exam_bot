import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    display_name: str
    is_enabled: bool
    updated_at: datetime | None
