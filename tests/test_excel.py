import pytest
import os
from datetime import date
import io
import uuid

from openpyxl import Workbook

from app.models.audit import AuditLog
from app.models.exam import Exam
from app.models.result import Result, ResultStatus
from app.models.user import User


def _create_user_and_exam(db_session):
    user = User(
        bale_user_id=100000001,
        phone_number="09121111111",
        national_code="1234567891",
        first_name="Test",
        last_name="User",
    )

    exam = Exam(
        title="Excel Import Test Exam",
        exam_code=f"EXCEL-{uuid.uuid4().hex[:8]}",
        exam_date=date(2026, 9, 3),
        total_score=100,
        passing_score=60,
    )

    db_session.add_all([user, exam])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(exam)

    return user, exam


def _create_excel_file(rows, columns=("national_code", "score")):
    workbook = Workbook()
    worksheet = workbook.active

    worksheet.append(list(columns))

    for row in rows:
        worksheet.append(list(row))

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return output


def _import_scores(client, exam_id, excel_file, token):
    headers = {
        "Authorization": f"Bearer {token}",
    }

    return client.post(
        "/api/excel/import-scores",
        params={"exam_id": str(exam_id)},
        headers=headers,
        files={
            "file": (
                "scores.xlsx",
                excel_file,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


def test_excel_import_success(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        (user.national_code, 85),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 1
    assert data["success_count"] == 1
    assert data["error_count"] == 0
    assert data["errors"] == []

    result = (
        db_session.query(Result)
        .filter(
            Result.user_id == user.id,
            Result.exam_id == exam.id,
        )
        .first()
    )

    assert result is not None
    assert float(result.score) == 85
    assert result.is_passed is True
    assert result.status == ResultStatus.RECORDED
    assert result.recorded_by_admin_id is not None


def test_excel_import_calculates_failed_result(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        (user.national_code, 45),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 1
    assert data["error_count"] == 0

    result = db_session.query(Result).first()

    assert result is not None
    assert float(result.score) == 45
    assert result.is_passed is False


def test_excel_import_rejects_invalid_national_code(
    client,
    db_session,
    super_admin_token,
):
    _, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        ("1234567890", 80),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 1
    assert data["success_count"] == 0
    assert data["error_count"] == 1

    assert data["errors"][0]["row_number"] == 2
    assert data["errors"][0]["national_code"] == "1234567890"

    assert db_session.query(Result).count() == 0


def test_excel_import_rejects_unknown_user(
    client,
    db_session,
    super_admin_token,
):
    _, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        ("9876543210", 80),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1

    assert "کاربری با این کد ملی ثبت‌نام نکرده است" in data["errors"][0]["error"]

    assert db_session.query(Result).count() == 0


def test_excel_import_rejects_invalid_score(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        (user.national_code, "abc"),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1
    assert "نمره نامعتبر" in data["errors"][0]["error"]

    assert db_session.query(Result).count() == 0


def test_excel_import_rejects_negative_score(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        (user.national_code, -1),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1

    assert db_session.query(Result).count() == 0


def test_excel_import_rejects_score_above_total_score(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        (user.national_code, 101),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1

    assert db_session.query(Result).count() == 0


def test_excel_import_rejects_duplicate_existing_result(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    existing_result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=70,
        is_passed=True,
        status=ResultStatus.RECORDED,
    )

    db_session.add(existing_result)
    db_session.commit()

    excel_file = _create_excel_file([
        (user.national_code, 80),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1

    assert db_session.query(Result).count() == 1


def test_excel_import_rejects_missing_national_code_column(
    client,
    db_session,
    super_admin_token,
):
    _, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file(
        [(80,)],
        columns=("score",),
    )

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1
    assert data["total_rows"] == 0


def test_excel_import_rejects_missing_score_column(
    client,
    db_session,
    super_admin_token,
):
    _, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file(
        [("1111111111",)],
        columns=("national_code",),
    )

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1
    assert data["total_rows"] == 0


def test_excel_import_rejects_unknown_exam(
    client,
    db_session,
    super_admin_token,
):
    user, _ = _create_user_and_exam(db_session)

    unknown_exam_id = uuid.uuid4()

    excel_file = _create_excel_file([
        (user.national_code, 80),
    ])

    response = _import_scores(
        client,
        unknown_exam_id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success_count"] == 0
    assert data["error_count"] == 1
    assert data["total_rows"] == 0

    assert db_session.query(Result).count() == 0


def test_excel_import_creates_audit_log(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    excel_file = _create_excel_file([
        (user.national_code, 85),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "excel_import",
            AuditLog.target_type == "exam",
            AuditLog.target_id == str(exam.id),
        )
        .first()
    )

    assert audit is not None
    assert audit.actor_type == "admin"
    assert audit.actor_id is not None
    assert audit.new_value == "success=1, errors=0"


def test_excel_import_handles_multiple_rows(
    client,
    db_session,
    super_admin_token,
):
    user1, exam = _create_user_and_exam(db_session)

    user2 = User(
        bale_user_id=100000002,
        phone_number="09121111112",
        national_code="1111111103",
        first_name="Test2",
        last_name="User2",
    )

    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    excel_file = _create_excel_file([
        (user1.national_code, 80),
        (user2.national_code, 55),
    ])

    response = _import_scores(
        client,
        exam.id,
        excel_file,
        super_admin_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 2
    assert data["success_count"] == 2
    assert data["error_count"] == 0

    results = (
        db_session.query(Result)
        .filter(Result.exam_id == exam.id)
        .all()
    )

    assert len(results) == 2

    scores = sorted(float(result.score) for result in results)

    assert scores == [55, 80]

def test_excel_import_rejects_invalid_file_extension(
    client,
    db_session,
    super_admin_token,
):
    _, exam = _create_user_and_exam(db_session)

    headers = {
        "Authorization": f"Bearer {super_admin_token}",
    }

    response = client.post(
        "/api/excel/import-scores",
        params={"exam_id": str(exam.id)},
        headers=headers,
        files={
            "file": (
                "scores.txt",
                b"not an excel file",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_excel_import_rejects_file_larger_than_10mb(
    client,
    db_session,
    super_admin_token,
):
    _, exam = _create_user_and_exam(db_session)

    headers = {
        "Authorization": f"Bearer {super_admin_token}",
    }

    large_content = b"x" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/api/excel/import-scores",
        params={"exam_id": str(exam.id)},
        headers=headers,
        files={
            "file": (
                "large.xlsx",
                large_content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 400


def test_excel_import_cleans_up_temp_file_when_service_fails(
    client,
    db_session,
    super_admin_token,
    monkeypatch,
):
    from app.api.routers import excel as excel_router

    _, exam = _create_user_and_exam(db_session)

    temp_file = None

    original_import = excel_router.import_scores_from_excel

    def failing_import(db, temp_path, exam_id, admin_id):
        nonlocal temp_file
        temp_file = temp_path
        raise RuntimeError("forced import failure")

    monkeypatch.setattr(
        excel_router,
        "import_scores_from_excel",
        failing_import,
    )

    excel_content = _create_excel_file([
        ("1234567891", 85),
    ])

    headers = {
        "Authorization": f"Bearer {super_admin_token}",
    }

    with pytest.raises(RuntimeError, match="forced import failure"):
        client.post(
            "/api/excel/import-scores",
            params={"exam_id": str(exam.id)},
            headers=headers,
            files={
                "file": (
                    "scores.xlsx",
                    excel_content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert temp_file is not None
    assert not os.path.exists(temp_file)

    monkeypatch.setattr(
        excel_router,
        "import_scores_from_excel",
        original_import,
    )



def test_excel_service_handles_unreadable_file(db_session, tmp_path):
    from app.services.excel_service import import_scores_from_excel

    broken_file = tmp_path / "broken.xlsx"
    broken_file.write_bytes(b"this is not a valid excel file")

    result = import_scores_from_excel(
        db_session,
        str(broken_file),
        "00000000-0000-0000-0000-000000000000",
        "test-admin",
    )

    assert result.total_rows == 0
    assert result.success_count == 0
    assert result.error_count == 1
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 0

def test_excel_import_cleanup_when_temp_file_already_removed(
    client,
    super_admin_token,
    monkeypatch,
):
    from app.api.routers import excel as excel_router

    temp_file = {"path": None}

    def fake_import(db, temp_path, exam_id, admin_id):
        temp_file["path"] = temp_path

        if os.path.exists(temp_path):
            os.remove(temp_path)

        raise RuntimeError("forced import failure")

    monkeypatch.setattr(
        excel_router,
        "import_scores_from_excel",
        fake_import,
    )

    with pytest.raises(RuntimeError, match="forced import failure"):
        client.post(
            "/api/excel/import-scores",
            params={
                "exam_id": "00000000-0000-0000-0000-000000000000",
            },
            headers={
                "Authorization": f"Bearer {super_admin_token}",
            },
            files={
                "file": (
                    "test.xlsx",
                    b"fake excel content",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert temp_file["path"] is not None
    assert not os.path.exists(temp_file["path"])



def test_excel_import_cleanup_when_temp_file_does_not_exist(
    client, super_admin_token, monkeypatch
):
    from app.api.routers import excel as excel_router

    temp_file = {"path": None}

    def fake_import(db, temp_path, exam_id, admin_id):
        temp_file["path"] = temp_path
        raise RuntimeError("forced import failure")

    monkeypatch.setattr(
        excel_router,
        "import_scores_from_excel",
        fake_import,
    )

    # Force the cleanup condition to take the False branch.
    monkeypatch.setattr(
        excel_router.os.path,
        "exists",
        lambda path: False,
    )

    with pytest.raises(RuntimeError, match="forced import failure"):
        client.post(
            "/api/excel/import-scores"
            "?exam_id=00000000-0000-0000-0000-000000000000",
            files={
                "file": (
                    "test.xlsx",
                    b"dummy excel content",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )

    assert temp_file["path"] is not None


def test_excel_import_cleanup_false_branch_returns_result(
    client, super_admin_token, monkeypatch
):
    from app.api.routers import excel as excel_router
    from app.schemas.result import ExcelImportResult

    expected_result = ExcelImportResult(
        total_rows=0,
        success_count=0,
        error_count=0,
        errors=[],
    )

    def fake_import(db, temp_path, exam_id, admin_id):
        return expected_result

    monkeypatch.setattr(
        excel_router,
        "import_scores_from_excel",
        fake_import,
    )

    monkeypatch.setattr(
        excel_router.os.path,
        "exists",
        lambda path: False,
    )

    response = client.post(
        "/api/excel/import-scores"
        "?exam_id=00000000-0000-0000-0000-000000000000",
        files={
            "file": (
                "test.xlsx",
                b"dummy excel content",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total_rows"] == 0
    assert response.json()["success_count"] == 0
    assert response.json()["error_count"] == 0
