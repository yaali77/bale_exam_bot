"""
اعلام خودکار نتیجه (بخش ۸) و اطلاع‌رسانی گروهی (بخش ۱۸ چک‌لیست).
"""
from sqlalchemy.orm import Session

from app.bot.client import bale_client
from app.core.logging import get_logger
from app.models.feature import FeatureFlag
from app.models.result import Result, ResultStatus
from app.models.user import User, UserStatus
from app.schemas.notification import BroadcastAudience

logger = get_logger(__name__)


def _is_feature_enabled(db: Session, key: str) -> bool:
    feature = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    return feature.is_enabled if feature else True


async def notify_result_published(db: Session, result: Result):
    """پس از انتشار یک نمره، در صورت فعال بودن قابلیت، به کاربر اطلاع می‌دهد"""
    if not _is_feature_enabled(db, "auto_notification"):
        return
    if result.notification_sent:
        return  # جلوگیری از ارسال تکراری

    user = db.query(User).filter(User.id == result.user_id).first()
    if not user or user.status == UserStatus.DISABLED:
        return

    status_text = "✅ قبول" if result.is_passed else "❌ مردود"
    text = (
        f"🔔 نتیجه آزمون «{result.exam.title}» منتشر شد.\n"
        f"نمره: {result.score}\nوضعیت: {status_text}\n\n"
        "برای مشاهده جزئیات و دریافت کارنامه، دستور /report را ارسال کنید."
    )

    try:
        await bale_client.send_message(user.bale_user_id, text)
        result.notification_sent = True
        db.commit()
    except Exception:
        logger.exception("Failed to notify user %s about result %s", user.id, result.id)


async def send_broadcast(db: Session, message: str, audience: BroadcastAudience, exam_id=None) -> tuple[int, int]:
    """ارسال پیام گروهی بر اساس مخاطب هدف. برمی‌گرداند: (تعداد ارسال موفق، تعداد ناموفق)"""
    query = db.query(User).filter(User.status == UserStatus.ACTIVE)

    if audience == BroadcastAudience.EXAM_PARTICIPANTS and exam_id:
        user_ids = db.query(Result.user_id).filter(Result.exam_id == exam_id)
        query = query.filter(User.id.in_(user_ids))
    elif audience == BroadcastAudience.PASSED and exam_id:
        user_ids = db.query(Result.user_id).filter(Result.exam_id == exam_id, Result.is_passed.is_(True))
        query = query.filter(User.id.in_(user_ids))
    elif audience == BroadcastAudience.FAILED and exam_id:
        user_ids = db.query(Result.user_id).filter(Result.exam_id == exam_id, Result.is_passed.is_(False))
        query = query.filter(User.id.in_(user_ids))

    users = query.all()
    sent, failed = 0, 0
    for user in users:
        try:
            await bale_client.send_message(user.bale_user_id, message)
            sent += 1
        except Exception:
            failed += 1
            logger.warning("Broadcast failed for user %s", user.id)

    return sent, failed
