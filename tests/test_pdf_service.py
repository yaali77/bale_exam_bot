import uuid
from datetime import date
from pathlib import Path

from app.models.result import Result, ResultStatus
from app.models.user import User
from app.models.exam import Exam
from app.services.pdf_service import (
    _generate_report_number,
    build_report_card_pdf,
)


def create_user(
    db_session,
    bale_user_id=200001,
    phone_number="09121111111",
    national_code="1234567891",
    first_name="علی",
    last_name="کرمی",
):
    user = User(
        bale_user_id=bale_user_id,
        phone_number=phone_number,
        national_code=national_code,
        first_name=first_name,
        last_name=last_name,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_exam(
    db_session,
    title="آزمون آزمایشی",
    exam_code=None,
):
    if exam_code is None:
        exam_code = f"TEST-{uuid.uuid4().hex[:12].upper()}"

    exam = Exam(
        title=title,
        exam_code=exam_code,
        exam_date=date.today(),
        total_score=100,
        passing_score=50,
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


def create_result(
    db_session,
    user,
    exam,
    score,
    is_passed,
    status=ResultStatus.PUBLISHED,
):
    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=score,
        is_passed=is_passed,
        status=status,
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    return result


def test_generate_report_number():
    report_number = _generate_report_number("1234567891")

    assert report_number.startswith("RC-7891-")
    assert len(report_number) == 18


def test_build_report_card_pdf_without_results(
    db_session,
    tmp_path,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=200001,
        phone_number="09121111111",
        national_code="1234567891",
    )

    monkeypatch.setattr(
        "app.services.pdf_service.settings.PDF_STORAGE_PATH",
        str(tmp_path),
    )

    report_number = "RC-7891-TEST01"

    file_path = build_report_card_pdf(
        db_session,
        user,
        str(tmp_path / "missing_qr.png"),
        report_number,
    )

    assert file_path == str(tmp_path / f"{report_number}.pdf")
    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 0


def test_build_report_card_pdf_with_results_and_missing_qr(
    db_session,
    tmp_path,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=200002,
        phone_number="09121111112",
        national_code="9876543210",
    )

    exam1 = create_exam(db_session, "آزمون اول")
    exam2 = create_exam(db_session, "آزمون دوم")
    exam3 = create_exam(db_session, "آزمون سوم")

    create_result(
        db_session,
        user,
        exam1,
        score=80,
        is_passed=True,
    )

    create_result(
        db_session,
        user,
        exam2,
        score=60,
        is_passed=False,
    )

    create_result(
        db_session,
        user,
        exam3,
        score=90,
        is_passed=True,
    )

    monkeypatch.setattr(
        "app.services.pdf_service.settings.PDF_STORAGE_PATH",
        str(tmp_path),
    )

    report_number = "RC-3210-TEST02"

    file_path = build_report_card_pdf(
        db_session,
        user,
        str(tmp_path / "missing_qr.png"),
        report_number,
    )

    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 0


def test_build_report_card_pdf_ignores_non_published_results(
    db_session,
    tmp_path,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=200003,
        phone_number="09121111113",
        national_code="1111111103",
    )

    published_exam = create_exam(
        db_session,
        "آزمون منتشرشده",
    )

    draft_exam = create_exam(
        db_session,
        "آزمون منتشرنشده",
    )

    create_result(
        db_session,
        user,
        published_exam,
        score=95,
        is_passed=True,
        status=ResultStatus.PUBLISHED,
    )

    create_result(
        db_session,
        user,
        draft_exam,
        score=10,
        is_passed=False,
        status=ResultStatus.RECORDED,
    )

    monkeypatch.setattr(
        "app.services.pdf_service.settings.PDF_STORAGE_PATH",
        str(tmp_path),
    )

    file_path = build_report_card_pdf(
        db_session,
        user,
        str(tmp_path / "missing_qr.png"),
        "RC-1103-TEST03",
    )

    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 0


def test_build_report_card_pdf_with_qr(
    db_session,
    tmp_path,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=200004,
        phone_number="09121111114",
        national_code="2222222202",
    )

    exam = create_exam(
        db_session,
        "آزمون QR",
    )

    create_result(
        db_session,
        user,
        exam,
        score=75,
        is_passed=True,
    )

    qr_path = tmp_path / "qr.png"

    from PIL import Image

    image = Image.new(
        "RGB",
        (100, 100),
        "white",
    )
    image.save(qr_path)

    monkeypatch.setattr(
        "app.services.pdf_service.settings.PDF_STORAGE_PATH",
        str(tmp_path),
    )

    file_path = build_report_card_pdf(
        db_session,
        user,
        str(qr_path),
        "RC-2202-TEST04",
    )

    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 0


def test_build_report_card_pdf_multiple_pages(
    db_session,
    tmp_path,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=200005,
        phone_number="09121111115",
        national_code="3333333303",
    )

    for index in range(35):
        exam = create_exam(
            db_session,
            f"آزمون شماره {index + 1}",
        )

        create_result(
            db_session,
            user,
            exam,
            score=50 + (index % 50),
            is_passed=index % 2 == 0,
        )

    monkeypatch.setattr(
        "app.services.pdf_service.settings.PDF_STORAGE_PATH",
        str(tmp_path),
    )

    file_path = build_report_card_pdf(
        db_session,
        user,
        str(tmp_path / "missing_qr.png"),
        "RC-3303-TEST05",
    )

    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 0
