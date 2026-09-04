"""جریان مکالمه اعتراض به نمره در بات (بخش ۱۲ چک‌لیست)"""
from sqlalchemy.orm import Session

from app.bot.client import bale_client
from app.core.audit import log_action
from app.models.feature import FeatureFlag
from app.models.objection import Objection
from app.models.result import Result, ResultStatus
from app.models.user import User

_pending_objection: dict[int, dict] = {}


def _is_feature_enabled(db: Session, key: str) -> bool:
    feature = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    return feature.is_enabled if feature else True


async def handle_objection_start(db: Session, bale_user_id: int, chat_id: int):
    if not _is_feature_enabled(db, "objection"):
        await bale_client.send_message(chat_id, "این قابلیت در حال حاضر غیرفعال است.")
        return

    user = db.query(User).filter(User.bale_user_id == bale_user_id).first()
    if not user:
        await bale_client.send_message(chat_id, "لطفاً ابتدا دستور /start را ارسال کنید.")
        return

    results = db.query(Result).filter(Result.user_id == user.id, Result.status == ResultStatus.PUBLISHED).all()
    if not results:
        await bale_client.send_message(chat_id, "نتیجه منتشرشده‌ای برای اعتراض ندارید.")
        return

    lines = ["به کدام آزمون اعتراض دارید؟ شماره ردیف را ارسال کنید:\n"]
    for i, r in enumerate(results, start=1):
        lines.append(f"{i}. {r.exam.title} - نمره: {r.score}")

    _pending_objection[bale_user_id] = {"step": "choosing_result", "results": [str(r.id) for r in results]}
    await bale_client.send_message(chat_id, "\n".join(lines))


async def handle_objection_input(db: Session, bale_user_id: int, chat_id: int, text: str) -> bool:
    """اگر کاربر در جریان اعتراض باشد، ورودی را پردازش می‌کند و True برمی‌گرداند؛ در غیر این صورت False"""
    state = _pending_objection.get(bale_user_id)
    if not state:
        return False

    if state["step"] == "choosing_result":
        try:
            index = int(text.strip()) - 1
            result_id = state["results"][index]
        except (ValueError, IndexError):
            await bale_client.send_message(chat_id, "❌ شماره نامعتبر است. دوباره تلاش کنید.")
            return True

        state["result_id"] = result_id
        state["step"] = "awaiting_description"
        await bale_client.send_message(chat_id, "لطفاً دلیل اعتراض خود را بنویسید:")
        return True

    if state["step"] == "awaiting_description":
        user = db.query(User).filter(User.bale_user_id == bale_user_id).first()
        objection = Objection(result_id=state["result_id"], user_id=user.id, description=text.strip())
        db.add(objection)
        db.commit()
        db.refresh(objection)

        log_action(db, action="objection_submitted", actor_type="user", actor_id=str(user.id),
                   target_type="objection", target_id=str(objection.id))

        _pending_objection.pop(bale_user_id, None)
        await bale_client.send_message(chat_id, "✅ اعتراض شما ثبت شد و پس از بررسی نتیجه به شما اطلاع داده می‌شود.")
        return True

    return False


def has_pending_objection(bale_user_id: int) -> bool:
    return bale_user_id in _pending_objection
