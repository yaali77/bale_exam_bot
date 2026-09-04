"""دستور /report در بات: ارسال کارنامه PDF به‌روز برای کاربر (بخش ۹ چک‌لیست)"""
from sqlalchemy.orm import Session

from app.bot.client import bale_client
from app.models.user import User, UserStatus


async def handle_report_card_request(db: Session, bale_user_id: int, chat_id: int):
    user = db.query(User).filter(User.bale_user_id == bale_user_id).first()
    if not user:
        await bale_client.send_message(chat_id, "شما هنوز ثبت‌نام نکرده‌اید. لطفاً دستور /start را ارسال کنید.")
        return
    if user.status == UserStatus.DISABLED:
        await bale_client.send_message(chat_id, "❌ حساب شما غیرفعال است.")
        return

    # Import محلی برای جلوگیری از Circular Import بین ماژول‌های bot و api
    from app.api.routers.reportcard import generate_or_refresh_report_card

    await bale_client.send_message(chat_id, "⏳ در حال آماده‌سازی کارنامه شما...")
    report_card = generate_or_refresh_report_card(db, user)

    if not report_card.pdf_path:
        await bale_client.send_message(chat_id, "در حال حاضر نتیجه منتشرشده‌ای برای صدور کارنامه موجود نیست.")
        return

    await bale_client.send_document(
        chat_id, report_card.pdf_path,
        caption=f"📄 کارنامه شما\nشماره کارنامه: {report_card.report_number}",
    )
