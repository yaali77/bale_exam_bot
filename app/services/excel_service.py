"""
پردازش ورود گروهی نمرات از فایل اکسل (بخش ۵ چک‌لیست).
ستون‌های موردنیاز: national_code, score
اعتبارسنجی هر سطر و گزارش خطاهای دقیق برمی‌گرداند.
"""
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.security import validate_national_code
from app.models.exam import Exam
from app.models.result import Result, ResultStatus
from app.models.user import User
from app.schemas.result import ExcelImportRowError, ExcelImportResult

REQUIRED_COLUMNS = {"national_code", "score"}


def import_scores_from_excel(db: Session, file_path: str, exam_id, admin_id) -> ExcelImportResult:
    try:
        df = pd.read_excel(file_path, dtype={"national_code": str})
    except Exception as exc:
        return ExcelImportResult(
            total_rows=0, success_count=0, error_count=1,
            errors=[ExcelImportRowError(row_number=0, error=f"فایل اکسل قابل خواندن نیست: {exc}")],
        )

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        return ExcelImportResult(
            total_rows=0, success_count=0, error_count=1,
            errors=[ExcelImportRowError(row_number=0, error=f"ستون‌های الزامی موجود نیست: {missing_cols}")],
        )

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return ExcelImportResult(
            total_rows=0, success_count=0, error_count=1,
            errors=[ExcelImportRowError(row_number=0, error="آزمون یافت نشد")],
        )

    errors: list[ExcelImportRowError] = []
    success_count = 0

    for idx, row in df.iterrows():
        row_number = idx + 2  # چون سطر ۱ هدر است
        national_code = str(row.get("national_code", "")).strip()
        raw_score = row.get("score")

        if not validate_national_code(national_code):
            errors.append(ExcelImportRowError(row_number=row_number, national_code=national_code, error="کد ملی نامعتبر"))
            continue

        try:
            score = Decimal(str(raw_score))
        except (InvalidOperation, TypeError):
            errors.append(ExcelImportRowError(row_number=row_number, national_code=national_code, error="نمره نامعتبر"))
            continue

        if score < 0 or score > exam.total_score:
            errors.append(ExcelImportRowError(
                row_number=row_number, national_code=national_code,
                error=f"نمره باید بین ۰ تا {exam.total_score} باشد",
            ))
            continue

        user = db.query(User).filter(User.national_code == national_code).first()
        if not user:
            errors.append(ExcelImportRowError(row_number=row_number, national_code=national_code, error="کاربری با این کد ملی ثبت‌نام نکرده است"))
            continue

        existing = db.query(Result).filter(Result.user_id == user.id, Result.exam_id == exam_id).first()
        if existing:
            errors.append(ExcelImportRowError(row_number=row_number, national_code=national_code, error="نمره این کاربر برای این آزمون قبلاً ثبت شده"))
            continue

        result = Result(
            user_id=user.id,
            exam_id=exam_id,
            score=score,
            is_passed=score >= exam.passing_score,
            status=ResultStatus.RECORDED,
            recorded_by_admin_id=admin_id,
        )
        db.add(result)
        success_count += 1

    db.commit()

    log_action(
        db, action="excel_import", actor_type="admin", actor_id=str(admin_id),
        target_type="exam", target_id=str(exam_id),
        new_value=f"success={success_count}, errors={len(errors)}",
    )

    return ExcelImportResult(
        total_rows=len(df), success_count=success_count, error_count=len(errors), errors=errors,
    )
