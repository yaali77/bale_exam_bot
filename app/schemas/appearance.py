import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class AppearanceUpdate(BaseModel):
    system_title: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    font_family: str | None = None
    welcome_message: str | None = None
    result_message_template: str | None = None
    error_message: str | None = None
    help_text: str | None = None

    @field_validator("primary_color", "secondary_color", "accent_color", "background_color")
    @classmethod
    def validate_hex_color(cls, v):
        if v is None:
            return v
        if not (v.startswith("#") and len(v) == 7):
            raise ValueError("رنگ باید به فرمت هگز مثل #0d3b66 باشد")
        return v


class AppearanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    system_title: str
    logo_url: str | None
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str
    font_family: str
    welcome_message: str | None
    result_message_template: str | None
    error_message: str | None
    help_text: str | None
    updated_at: datetime | None
