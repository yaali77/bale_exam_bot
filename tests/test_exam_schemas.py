from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

import pytest
from pydantic import ValidationError

from app.models.exam import ExamStatus
from app.schemas.exam import ExamCreate, ExamUpdate, ExamOut


def test_exam_create_passing_score_greater_than_total():
    with pytest.raises(ValidationError):
        ExamCreate(
            title="آزمون تست",
            exam_code="EXAM-001",
            exam_date=date.today(),
            total_score=Decimal("100"),
            passing_score=Decimal("101"),
        )


def test_exam_create_valid_passing_score():
    exam = ExamCreate(
        title="آزمون تست",
        exam_code="EXAM-001",
        exam_date=date.today(),
        total_score=Decimal("100"),
        passing_score=Decimal("50"),
    )

    assert exam.total_score == Decimal("100")
    assert exam.passing_score == Decimal("50")


def test_exam_update_total_score_must_be_positive():
    with pytest.raises(ValidationError):
        ExamUpdate(total_score=Decimal("0"))


def test_exam_update_passing_score_cannot_be_negative():
    with pytest.raises(ValidationError):
        ExamUpdate(passing_score=Decimal("-1"))


def test_exam_update_passing_score_cannot_exceed_total_score():
    with pytest.raises(ValidationError):
        ExamUpdate(
            total_score=Decimal("100"),
            passing_score=Decimal("101"),
        )


def test_exam_update_valid_scores():
    exam = ExamUpdate(
        title="آزمون به‌روزشده",
        total_score=Decimal("100"),
        passing_score=Decimal("60"),
        status=ExamStatus.READY_FOR_REVIEW,
        is_active=True,
    )

    assert exam.title == "آزمون به‌روزشده"
    assert exam.total_score == Decimal("100")
    assert exam.passing_score == Decimal("60")
    assert exam.status == ExamStatus.READY_FOR_REVIEW
    assert exam.is_active is True


def test_exam_update_without_scores_is_valid():
    exam = ExamUpdate(
        title="فقط عنوان",
    )

    assert exam.title == "فقط عنوان"
    assert exam.total_score is None
    assert exam.passing_score is None


def test_exam_out_from_attributes():
    class ExamObject:
        id = uuid.uuid4()
        title = "آزمون خروجی"
        exam_code = "EXAM-OUT-001"
        exam_date = date.today()
        total_score = Decimal("100")
        passing_score = Decimal("60")
        description = "توضیحات آزمون"
        status = ExamStatus.PUBLISHED
        results_publish_date = datetime.now(timezone.utc)
        is_active = True
        created_at = datetime.now(timezone.utc)

    exam = ExamOut.model_validate(ExamObject(), from_attributes=True)

    assert exam.title == "آزمون خروجی"
    assert exam.exam_code == "EXAM-OUT-001"
    assert exam.total_score == Decimal("100")
    assert exam.passing_score == Decimal("60")
    assert exam.status == ExamStatus.PUBLISHED
    assert exam.is_active is True
