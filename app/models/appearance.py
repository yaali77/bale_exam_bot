"""
تنظیمات ظاهری قابل ویرایش توسط ادمین بدون تغییر کد (بخش ۱۶ چک‌لیست).
این جدول همیشه دقیقاً یک رکورد دارد (Singleton) که هم پنل ادمین و هم بات از آن می‌خوانند.
"""
import uuid

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func

from app.core.db_types import GUID
from app.database import Base


class AppearanceSettings(Base):
    __tablename__ = "appearance_settings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # هویت و برند
    system_title = Column(String(150), nullable=False, default="سامانه اعلام نتایج آزمون")
    logo_url = Column(String(500), nullable=True)

    # رنگ‌بندی
    primary_color = Column(String(7), nullable=False, default="#0d3b66")
    secondary_color = Column(String(7), nullable=False, default="#082744")
    accent_color = Column(String(7), nullable=False, default="#c9a227")
    background_color = Column(String(7), nullable=False, default="#f7f7f5")

    # فونت
    font_family = Column(String(150), nullable=False, default="Vazirmatn, IRANSans, Tahoma, sans-serif")

    # متون قابل تغییر
    welcome_message = Column(Text, nullable=True, default="سلام 👋 خوش آمدید.")
    result_message_template = Column(Text, nullable=True, default="نمره: {score} | وضعیت: {status}")
    error_message = Column(Text, nullable=True, default="خطایی رخ داد. لطفاً دوباره تلاش کنید.")
    help_text = Column(Text, nullable=True)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by_admin_id = Column(GUID(), nullable=True)
