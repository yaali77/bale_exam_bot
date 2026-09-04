"""جریان مکالمه درخواست اصلاح اطلاعات در بات (بخش ۱۱ چک‌لیست)"""
from sqlalchemy.orm import Session

from app.bot.client import bale_client
from app.core.audit import log_action
from app.models.correction import CorrectionRequest
from app.models.feature import FeatureFlag
from app.models.user import User

_pending_correction: dict[int, dict] = {}

FIELD_LABELS = {"first_name": "نام", "last_name": "نام خانوادگی", "phone_number": "شماره تلفن"}


def _is_feature_enabled(db: Session, key: str) -> bool:
    feature = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    return feature.is_enabled if feature else True


async def handle_correction_start(db: Session, bale_user_id: int, chat_id: int):
    if not _is_feature_enabled(db, "correction_request"):
        await bale_client.send_message(chat_id, "این قابلیت در حال حاضر غیرفعال است.")
        return

    user = db.query(User).filter(User.bale_user_id == bale_user_id).first()
    if not user:
        await bale_client.send_message(chat_id, "لطفاً ابتدا دستور /start را ارسال کنید.")
        return

    options = "\n".join(f"{i+1}. {label}" for i, label in enumerate(FIELD_LABELS.values()))
    _pending_correction[bale_user_id] = {"step": "choosing_field", "fields": list(FIELD_LABELS.keys())}
    await bale_client.send_message(chat_id, f"کدام اطلاعات نیاز به اصلاح دارد؟\n{options}")


async def handle_correction_input(db: Session, bale_user_id: int, chat_id: int, text: str) -> bool:
    state = _pending_correction.get(bale_user_id)
    if not state:
        return False

    user = db.query(User).filter(User.bale_user_id == bale_user_id).first()

    if state["step"] == "choosing_field":
        try:
            field = state["fields"][int(text.strip()) - 1]
        except (ValueError, IndexError):
            await bale_client.send_message(chat_id, "❌ گزینه نامعتبر است.")
            return True
        state["field"] = field
        state["step"] = "awaiting_value"
        await bale_client.send_message(chat_id, f"مقدار جدید برای «{FIELD_LABELS[field]}» را ارسال کنید:")
        return True

    if state["step"] == "awaiting_value":
        field = state["field"]
        request = CorrectionRequest(
            user_id=user.id,
            field_name=field,
            previous_value=getattr(user, field, None),
            requested_value=text.strip(),
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        log_action(db, action="correction_requested", actor_type="user", actor_id=str(user.id),
                   target_type="correction_request", target_id=str(request.id), new_value=text.strip())

        _pending_correction.pop(bale_user_id, None)
        await bale_client.send_message(chat_id, "✅ درخواست اصلاح شما ثبت شد و پس از بررسی ادمین اعمال می‌شود.")
        return True

    return False


def has_pending_correction(bale_user_id: int) -> bool:
    return bale_user_id in _pending_correction
