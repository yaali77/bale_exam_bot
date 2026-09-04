from sqlalchemy.orm import Session

from app.bot.client import bale_client
from app.core.security import validate_national_code
from app.models.user import User, UserStatus
from app.models.result import Result, ResultStatus
from app.services.appearance_service import get_appearance


async def handle_result_inquiry(db: Session, bale_user_id: int, chat_id: int, national_code: str):
    appearance = get_appearance(db)
    error_message = appearance.error_message or "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."

    if not validate_national_code(national_code):
        await bale_client.send_message(chat_id, "❌ کد ملی نامعتبر است.")
        return

    user = db.query(User).filter(User.bale_user_id == bale_user_id).first()
    if not user:
        await bale_client.send_message(chat_id, "شما هنوز ثبت‌نام نکرده‌اید. لطفاً دستور /start را ارسال کنید.")
        return

    if user.status == UserStatus.DISABLED:
        await bale_client.send_message(chat_id, error_message)
        return

    # جلوگیری از مشاهده نتیجه شخص دیگر: فقط کد ملی متعلق به همان حساب پذیرفته می‌شود
    if user.national_code != national_code:
        await bale_client.send_message(chat_id, error_message)
        return

    results = (
        db.query(Result)
        .filter(Result.user_id == user.id, Result.status == ResultStatus.PUBLISHED)
        .order_by(Result.published_at.desc())
        .all()
    )

    if not results:
        await bale_client.send_message(chat_id, "📭 در حال حاضر نتیجه منتشرشده‌ای برای شما موجود نیست.")
        return

    template = appearance.result_message_template or "نمره: {score} | وضعیت: {status}"

    lines = ["📋 نتایج آزمون‌های شما:\n"]
    for r in results:
        status_text = "✅ قبول" if r.is_passed else "❌ مردود"
        line = template.format(score=r.score, status=status_text)
        lines.append(f"• {r.exam.title}\n  {line}\n")

    await bale_client.send_message(chat_id, "\n".join(lines))
