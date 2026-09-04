from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database import get_db
from app.models.admin import Admin
from app.models.correction import CorrectionRequest, RequestStatus
from app.models.exam import Exam
from app.models.objection import Objection, ObjectionStatus
from app.models.result import Result, ResultStatus
from app.models.user import User, UserStatus

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db), admin: Admin = Depends(require_permission("view"))):
    """آمار کلی داشبورد پنل مدیریت (بخش ۱۳ چک‌لیست)"""
    return {
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.status == UserStatus.ACTIVE).count(),
        "total_exams": db.query(Exam).filter(Exam.is_active.is_(True)).count(),
        "total_results": db.query(Result).count(),
        "unpublished_results": db.query(Result).filter(Result.status != ResultStatus.PUBLISHED).count(),
        "pending_correction_requests": db.query(CorrectionRequest).filter(CorrectionRequest.status == RequestStatus.PENDING).count(),
        "pending_objections": db.query(Objection).filter(Objection.status == ObjectionStatus.PENDING).count(),
    }
