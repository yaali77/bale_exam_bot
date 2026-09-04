import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.audit import log_action
from app.database import get_db
from app.models.admin import Admin
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamOut, ExamUpdate

router = APIRouter(prefix="/api/exams", tags=["Exams"])


@router.get("", response_model=list[ExamOut])
def list_exams(db: Session = Depends(get_db), admin: Admin = Depends(require_permission("view"))):
    return db.query(Exam).order_by(Exam.exam_date.desc()).all()


@router.post("", response_model=ExamOut)
def create_exam(payload: ExamCreate, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("create"))):
    if db.query(Exam).filter(Exam.exam_code == payload.exam_code).first():
        raise HTTPException(status_code=400, detail="این کد آزمون قبلاً ثبت شده است")

    exam = Exam(**payload.model_dump())
    db.add(exam)
    db.commit()
    db.refresh(exam)

    log_action(db, action="exam_created", actor_type="admin", actor_id=str(admin.id),
               target_type="exam", target_id=str(exam.id), new_value=exam.exam_code)
    return exam


@router.get("/{exam_id}", response_model=ExamOut)
def get_exam(exam_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("view"))):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    return exam


@router.patch("/{exam_id}", response_model=ExamOut)
def update_exam(exam_id: uuid.UUID, payload: ExamUpdate, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("edit"))):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(exam, field, value)
    db.commit()
    db.refresh(exam)

    log_action(db, action="exam_updated", actor_type="admin", actor_id=str(admin.id),
               target_type="exam", target_id=str(exam.id), new_value=str(changes))
    return exam


@router.delete("/{exam_id}")
def delete_exam(exam_id: uuid.UUID, db: Session = Depends(get_db), admin: Admin = Depends(require_permission("delete"))):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")

    exam.is_active = False  # حذف نرم به‌جای حذف فیزیکی، برای حفظ یکپارچگی نتایج مرتبط
    db.commit()

    log_action(db, action="exam_deactivated", actor_type="admin", actor_id=str(admin.id),
               target_type="exam", target_id=str(exam.id))
    return {"detail": "آزمون غیرفعال شد"}
