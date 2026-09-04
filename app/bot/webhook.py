from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.core.logging import get_logger
from app.bot.handlers.registration import handle_start, handle_contact, handle_national_code_input
from app.bot.handlers.reportcard import handle_report_card_request
from app.bot.handlers.objection import handle_objection_start, handle_objection_input, has_pending_objection
from app.bot.handlers.correction import handle_correction_start, handle_correction_input, has_pending_correction

logger = get_logger(__name__)
router = APIRouter()


@router.post(settings.BALE_WEBHOOK_PATH)
async def bale_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    # اعتبارسنجی امضای Webhook برای جلوگیری از درخواست‌های جعلی
    if settings.BALE_WEBHOOK_SECRET and x_webhook_secret != settings.BALE_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    update = await request.json()
    logger.debug("Received update: %s", update)

    message = update.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    bale_user_id = message["from"]["id"]
    text = message.get("text", "")
    contact = message.get("contact")

    try:
        if text == "/start":
            await handle_start(db, bale_user_id, chat_id)

        elif contact:
            await handle_contact(
                db, bale_user_id, chat_id,
                phone_number=contact["phone_number"],
                contact_user_id=contact.get("user_id", bale_user_id),
            )

        elif text == "/report":
            await handle_report_card_request(db, bale_user_id, chat_id)

        elif text == "/objection":
            await handle_objection_start(db, bale_user_id, chat_id)

        elif text == "/correction":
            await handle_correction_start(db, bale_user_id, chat_id)

        elif text and has_pending_objection(bale_user_id):
            await handle_objection_input(db, bale_user_id, chat_id, text)

        elif text and has_pending_correction(bale_user_id):
            await handle_correction_input(db, bale_user_id, chat_id, text)

        elif text:
            # هر متن دیگر: یا ادامه ثبت‌نام (کد ملی) یا استعلام نتیجه با کد ملی
            await handle_national_code_input(db, bale_user_id, chat_id, text)

    except Exception:
        logger.exception("Error handling update for user %s", bale_user_id)
        # خطا برای کاربر نمایش داده نمی‌شود؛ فقط لاگ می‌شود

    return {"ok": True}
