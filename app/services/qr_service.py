"""
تولید QR Code برای هر کارنامه و مدیریت اعتبارسنجی آن (بخش ۱۰ چک‌لیست).
QR به یک صفحه عمومی اعتبارسنجی لینک می‌شود که فقط حداقل اطلاعات لازم را نشان می‌دهد.
"""
import os
import uuid

import qrcode

from app.config import settings


def generate_verification_code() -> str:
    """یک کد اعتبارسنجی یکتا و غیرقابل حدس تولید می‌کند"""
    return uuid.uuid4().hex


def generate_qr_image(verification_code: str) -> str:
    """تولید تصویر QR که به صفحه اعتبارسنجی عمومی اشاره می‌کند. مسیر فایل ذخیره‌شده را برمی‌گرداند."""
    os.makedirs(settings.QR_STORAGE_PATH, exist_ok=True)

    verify_url = f"{settings.PUBLIC_BASE_URL}/verify/{verification_code}"
    img = qrcode.make(verify_url)

    file_path = os.path.join(settings.QR_STORAGE_PATH, f"{verification_code}.png")
    img.save(file_path)
    return file_path
