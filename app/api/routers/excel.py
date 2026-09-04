import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.config import settings
from app.database import get_db
from app.models.admin import Admin
from app.schemas.result import ExcelImportResult
from app.services.excel_service import import_scores_from_excel

router = APIRouter(prefix="/api/excel", tags=["Excel"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


@router.post("/import-scores", response_model=ExcelImportResult)
async def import_scores(
    exam_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("create")),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="فقط فایل‌های اکسل (.xlsx, .xls) پذیرفته می‌شوند")

    os.makedirs(settings.EXCEL_STORAGE_PATH, exist_ok=True)
    temp_path = os.path.join(settings.EXCEL_STORAGE_PATH, f"upload_{uuid.uuid4().hex}{ext}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم فایل نباید بیشتر از ۱۰ مگابایت باشد")

    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        result = import_scores_from_excel(db, temp_path, exam_id, admin.id)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return result
