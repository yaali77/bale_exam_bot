import uuid
from datetime import date
from decimal import Decimal

from app.models.exam import Exam, ExamStatus


def exam_payload(
    exam_code="EXAM-001",
    title="آزمون آزمایشی",
):
    return {
        "title": title,
        "exam_code": exam_code,
        "exam_date": "2026-09-10",
        "total_score": "100",
        "passing_score": "50",
        "description": "آزمون تستی",
    }


def create_exam(db_session, **kwargs):
    data = {
        "title": "آزمون تستی",
        "exam_code": "EXAM-DB-001",
        "exam_date": date(2026, 9, 10),
        "total_score": Decimal("100"),
        "passing_score": Decimal("50"),
        "description": "توضیحات آزمون",
    }
    data.update(kwargs)

    exam = Exam(**data)
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


def test_list_exams_empty(client, super_admin_token):
    response = client.get(
        "/api/exams",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_exams_returns_exams(
    client,
    db_session,
    super_admin_token,
):
    create_exam(
        db_session,
        exam_code="EXAM-001",
        title="آزمون اول",
        exam_date=date(2026, 9, 10),
    )
    create_exam(
        db_session,
        exam_code="EXAM-002",
        title="آزمون دوم",
        exam_date=date(2026, 9, 20),
    )

    response = client.get(
        "/api/exams",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert data[0]["exam_code"] == "EXAM-002"
    assert data[1]["exam_code"] == "EXAM-001"


def test_create_exam_success(
    client,
    db_session,
    super_admin_token,
):
    response = client.post(
        "/api/exams",
        json=exam_payload(),
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "آزمون آزمایشی"
    assert data["exam_code"] == "EXAM-001"
    assert data["exam_date"] == "2026-09-10"
    assert Decimal(str(data["total_score"])) == Decimal("100")
    assert Decimal(str(data["passing_score"])) == Decimal("50")
    assert data["description"] == "آزمون تستی"
    assert data["status"] == "draft"
    assert data["is_active"] is True

    exam = (
        db_session.query(Exam)
        .filter(Exam.exam_code == "EXAM-001")
        .first()
    )

    assert exam is not None
    assert exam.title == "آزمون آزمایشی"


def test_create_exam_duplicate_code(
    client,
    db_session,
    super_admin_token,
):
    create_exam(
        db_session,
        exam_code="DUPLICATE-001",
    )

    response = client.post(
        "/api/exams",
        json=exam_payload(
            exam_code="DUPLICATE-001",
            title="آزمون تکراری",
        ),
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 400
    assert "exam" in response.json()["detail"].lower() or response.json()["detail"]


def test_get_exam_success(
    client,
    db_session,
    super_admin_token,
):
    exam = create_exam(
        db_session,
        exam_code="GET-001",
        title="آزمون دریافت",
    )

    response = client.get(
        f"/api/exams/{exam.id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(exam.id)
    assert data["exam_code"] == "GET-001"
    assert data["title"] == "آزمون دریافت"


def test_get_exam_not_found(
    client,
    super_admin_token,
):
    exam_id = uuid.uuid4()

    response = client.get(
        f"/api/exams/{exam_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 404


def test_update_exam_success(
    client,
    db_session,
    super_admin_token,
):
    exam = create_exam(
        db_session,
        exam_code="UPDATE-001",
        title="عنوان قدیمی",
        description="توضیح قدیمی",
    )

    response = client.patch(
        f"/api/exams/{exam.id}",
        json={
            "title": "عنوان جدید",
            "passing_score": "60",
            "description": "توضیح جدید",
            "status": "published",
        },
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "عنوان جدید"
    assert Decimal(str(data["passing_score"])) == Decimal("60")
    assert data["description"] == "توضیح جدید"
    assert data["status"] == "published"

    db_session.expire_all()

    updated = db_session.query(Exam).filter(Exam.id == exam.id).first()

    assert updated.title == "عنوان جدید"
    assert updated.status == ExamStatus.PUBLISHED


def test_update_exam_multiple_fields(
    client,
    db_session,
    super_admin_token,
):
    exam = create_exam(
        db_session,
        exam_code="UPDATE-002",
        title="عنوان اولیه",
        exam_date=date(2026, 9, 10),
        total_score=Decimal("100"),
        passing_score=Decimal("50"),
    )

    response = client.patch(
        f"/api/exams/{exam.id}",
        json={
            "title": "عنوان اصلاح‌شده",
            "exam_date": "2026-10-01",
            "total_score": "120",
            "passing_score": "70",
            "is_active": False,
        },
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "عنوان اصلاح‌شده"
    assert data["exam_date"] == "2026-10-01"
    assert Decimal(str(data["total_score"])) == Decimal("120")
    assert Decimal(str(data["passing_score"])) == Decimal("70")
    assert data["is_active"] is False


def test_update_exam_not_found(
    client,
    super_admin_token,
):
    exam_id = uuid.uuid4()

    response = client.patch(
        f"/api/exams/{exam_id}",
        json={"title": "عنوان جدید"},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 404


def test_update_exam_with_empty_payload(
    client,
    db_session,
    super_admin_token,
):
    exam = create_exam(
        db_session,
        exam_code="UPDATE-EMPTY-001",
        title="بدون تغییر",
    )

    response = client.patch(
        f"/api/exams/{exam.id}",
        json={},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "بدون تغییر"
    assert data["exam_code"] == "UPDATE-EMPTY-001"


def test_delete_exam_success(
    client,
    db_session,
    super_admin_token,
):
    exam = create_exam(
        db_session,
        exam_code="DELETE-001",
        title="آزمون حذف نرم",
    )

    assert exam.is_active is True

    response = client.delete(
        f"/api/exams/{exam.id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    assert "detail" in response.json()

    db_session.expire_all()

    deleted_exam = (
        db_session.query(Exam)
        .filter(Exam.id == exam.id)
        .first()
    )

    assert deleted_exam is not None
    assert deleted_exam.is_active is False


def test_delete_exam_not_found(
    client,
    super_admin_token,
):
    exam_id = uuid.uuid4()

    response = client.delete(
        f"/api/exams/{exam_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 404
def test_exam_repr():
    from app.models.exam import Exam

    exam = Exam(
        exam_code="REP001",
        title="Representation Test",
    )

    result = repr(exam)

    assert "REP001" in result
