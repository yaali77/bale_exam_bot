"""
جریان ثبت‌نام کاربر:
1. کاربر /start را می‌زند
2. ربات شماره تماس واقعی را از طریق دکمه Contact درخواست می‌کند (نه تایپی)
3. ربات کد ملی را درخواست می‌کند
4. اعتبارسنجی کد ملی + عدم تکراری بودن + تطبیق با شماره تلفن
5. ذخیره دائمی کاربر
"""
from sqlalchemy.orm import Session

from app.bot.client import bale_client
from app.core.audit import log_action
from app.core.logging import get_logger
from app.core.security import validate_national_code
from app.models.user import User, UserStatus
from app.services.appearance_service import get_appearance

logger = get_logger(__name__)

# حافظه موقت وضعیت مکالمه هر کاربر (در Production بهتر است Redis استفاده شود)
_pending_registration: dict[int, dict] = {}


async def handle_start(db: Session, bale_user_id: int, chat_id: int):
    appearance = get_appearance(db)

    existing = db.query(User).filter(User.bale_user_id == bale_user_id).first()
    if existing:
        if existing.status == UserStatus.DISABLED:
            await bale_client.send_message(chat_id, appearance.error_message or "❌ حساب شما غیرفعال شده است.")
            return
        await bale_client.send_message(
            chat_id,
            f"سلام {existing.first_name or ''} 👋\nخوش آمدید. برای دریافت نتیجه، کد ملی خود را ارسال کنید."
        )
        return

    await bale_client.request_contact_keyboard(
        chat_id,
        f"{appearance.welcome_message or 'سلام 👋 خوش آمدید.'}\nبرای ثبت‌نام، لطفاً شماره تماس خود را با دکمه زیر ارسال کنید."
    )
    _pending_registration[bale_user_id] = {"step": "awaiting_contact"}


async def handle_contact(db: Session, bale_user_id: int, chat_id: int, phone_number: str, contact_user_id: int):
    # کنترل اینکه شماره ارسالی متعلق به همان کاربر باشد (نه Contact شخص دیگر)
    if contact_user_id != bale_user_id:
        await bale_client.send_message(chat_id, "⚠️ لطفاً شماره تماس خودتان را ارسال کنید.")
        return

    normalized_phone = phone_number.lstrip("+").replace("98", "0", 1) if phone_number.startswith("+98") else phone_number

    if db.query(User).filter(User.phone_number == normalized_phone).first():
        await bale_client.send_message(chat_id, "⚠️ این شماره قبلاً ثبت شده است.")
        _pending_registration.pop(bale_user_id, None)
        return

    _pending_registration[bale_user_id] = {"step": "awaiting_national_code", "phone_number": normalized_phone}
    await bale_client.send_message(chat_id, "✅ شماره دریافت شد.\nحالا لطفاً کد ملی ۱۰ رقمی خود را ارسال کنید.")


async def handle_national_code_input(db: Session, bale_user_id: int, chat_id: int, text: str):
    state = _pending_registration.get(bale_user_id)

    # اگر کاربر از قبل ثبت‌نام کرده: این ورودی یک استعلام است نه ثبت‌نام
    if not state or state.get("step") != "awaiting_national_code":
        from app.bot.handlers.query import handle_result_inquiry
        await handle_result_inquiry(db, bale_user_id, chat_id, text.strip())
        return

    national_code = text.strip()
    if not validate_national_code(national_code):
        await bale_client.send_message(chat_id, "❌ کد ملی نامعتبر است. لطفاً یک کد ملی ۱۰ رقمی صحیح ارسال کنید.")
        return

    if db.query(User).filter(User.national_code == national_code).first():
        await bale_client.send_message(chat_id, "⚠️ این کد ملی قبلاً به حساب دیگری متصل شده است.")
        _pending_registration.pop(bale_user_id, None)
        return

    new_user = User(
        bale_user_id=bale_user_id,
        phone_number=state["phone_number"],
        national_code=national_code,
        status=UserStatus.ACTIVE,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_action(
        db, action="registration", actor_type="user", actor_id=str(new_user.id),
        target_type="user", target_id=str(new_user.id), new_value=national_code,
    )

    _pending_registration.pop(bale_user_id, None)
    await bale_client.send_message(
        chat_id,
        "🎉 ثبت‌نام شما با موفقیت انجام شد.\nهر زمان نتیجه آزمون منتشر شود، به شما اطلاع داده می‌شود.\n"
        "برای استعلام نتیجه، در هر زمان کد ملی خود را ارسال کنید."
    )
