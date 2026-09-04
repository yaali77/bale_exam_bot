from sqlalchemy import Column, String, Boolean, DateTime
from app.core.db_types import GUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class FeatureFlag(Base):
    """
    کلید اصلی قابلیت 'مدیریت قابلیت‌ها' که به ادمین اجازه می‌دهد
    هر بخش از سیستم را بدون تغییر کد فعال/غیرفعال کند.
    """
    __tablename__ = "feature_flags"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    key = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(150), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# کلیدهای پیش‌فرض قابلیت‌ها طبق بخش ۱۵ چک‌لیست
DEFAULT_FEATURES = [
    ("registration", "ثبت‌نام"),
    ("inquiry", "استعلام نتیجه"),
    ("history", "سوابق"),
    ("report_card", "کارنامه"),
    ("pdf_export", "خروجی PDF"),
    ("qr_verification", "اعتبارسنجی QR"),
    ("auto_notification", "اعلام خودکار نتیجه"),
    ("objection", "اعتراض به نمره"),
    ("correction_request", "درخواست اصلاح اطلاعات"),
    ("excel_import", "ورود اکسل"),
    ("broadcast_notification", "اطلاع‌رسانی گروهی"),
    ("reports", "گزارش‌ها"),
]
