from datetime import date
import uuid

from app.core.security import hash_password
from app.models.admin import Admin, AdminRole
from app.models.audit import AuditLog
from app.models.exam import Exam
from app.models.objection import Objection, ObjectionStatus
from app.models.result import Result, ResultHistory, ResultStatus
from app.models.user import User


def create_objection_data(db_session, result_status=ResultStatus.PUBLISHED):
    user = User(
        bale_user_id=987650001,
        phone_number="09121110001",
        national_code="1234567801",
        first_name="Test",
        last_name="User",
    )

    exam = Exam(
        title="Objection Test Exam",
        exam_code=f"OBJ-{uuid.uuid4().hex[:8]}",
        exam_date=date(2026, 9, 3),
        total_score=100,
        passing_score=60,
    )

    admin = Admin(
        username=f"objection_admin_{uuid.uuid4().hex[:8]}",
        full_name="Objection Admin",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
    )

    db_session.add_all([user, exam, admin])
    db_session.commit()

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=50,
        is_passed=False,
        status=result_status,
        recorded_by_admin_id=admin.id,
        notification_sent=True,
    )

    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    objection = Objection(
        result_id=result.id,
        user_id=user.id,
        description="اعتراض تستی به نمره",
        status=ObjectionStatus.PENDING,
    )

    db_session.add(objection)
    db_session.commit()
    db_session.refresh(objection)

    return user, exam, admin, result, objection


def login_admin(client, username, password="StrongPass123"):
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def test_list_objections_requires_auth(client):
    response = client.get("/api/objections")
    assert response.status_code == 401


def test_list_objections_returns_all(client, db_session, super_admin_token):
    _, _, _, _, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        "/api/objections",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(objection.id)


def test_list_objections_without_status_filter(client, db_session, super_admin_token):
    _, _, _, _, pending = create_objection_data(db_session)

    second = Objection(
        result_id=pending.result_id,
        user_id=pending.user_id,
        description="اعتراض دوم",
        status=ObjectionStatus.REJECTED,
    )

    db_session.add(second)
    db_session.commit()

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        "/api/objections",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_objections_filters_by_status(client, db_session, super_admin_token):
    _, _, _, _, pending = create_objection_data(db_session)

    rejected = Objection(
        result_id=pending.result_id,
        user_id=pending.user_id,
        description="اعتراض رد شده",
        status=ObjectionStatus.REJECTED,
    )

    db_session.add(rejected)
    db_session.commit()

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        "/api/objections",
        params={"status": "rejected"},
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["status"] == "rejected"


def test_support_can_view_objections_but_cannot_review(
    client,
    db_session,
):
    _, _, _, _, objection = create_objection_data(db_session)

    support = Admin(
        username=f"support_{uuid.uuid4().hex[:8]}",
        full_name="Support Admin",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SUPPORT,
        is_active=True,
    )

    db_session.add(support)
    db_session.commit()

    headers = login_admin(client, support.username)

    response = client.get(
        "/api/objections",
        headers=headers,
    )

    assert response.status_code == 200

    review = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "rejected",
            "resolution_note": "تست عدم دسترسی",
        },
        headers=headers,
    )

    assert review.status_code == 403


def test_review_missing_objection_returns_404(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    missing_id = uuid.uuid4()

    response = client.post(
        f"/api/objections/{missing_id}/review",
        json={
            "status": "rejected",
            "resolution_note": "اعتراض پیدا نشد",
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_review_rejected_objection_without_new_score(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, result, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "rejected",
            "resolution_note": "نمره مورد تأیید است",
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(objection)
    db_session.refresh(result)

    assert objection.status == ObjectionStatus.REJECTED
    assert objection.resolution_note == "نمره مورد تأیید است"
    assert objection.reviewed_by_admin_id is not None
    assert objection.resolved_at is not None

    assert result.score == 50
    assert result.is_passed is False


def test_review_approved_without_new_score(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, result, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "approved",
            "resolution_note": "اعتراض پذیرفته شد بدون اصلاح نمره",
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(result)
    db_session.refresh(objection)

    assert objection.status == ObjectionStatus.APPROVED
    assert objection.reviewed_by_admin_id is not None
    assert objection.resolved_at is not None

    assert result.score == 50
    assert result.is_passed is False


def test_review_approved_with_valid_new_score(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, result, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "approved",
            "resolution_note": "اصلاح نمره",
            "new_score": 80,
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(result)
    db_session.refresh(objection)

    assert objection.status == ObjectionStatus.APPROVED
    assert objection.reviewed_by_admin_id is not None
    assert objection.resolved_at is not None

    assert result.score == 80
    assert result.is_passed is True
    assert result.notification_sent is False

    history = (
        db_session.query(ResultHistory)
        .filter(ResultHistory.result_id == result.id)
        .all()
    )

    assert len(history) == 1

    assert history[0].previous_score == 50
    assert history[0].new_score == 80
    assert history[0].previous_status == ResultStatus.PUBLISHED
    assert history[0].new_status == ResultStatus.PUBLISHED
    assert history[0].changed_by_admin_id is not None


def test_review_approved_new_score_below_passing(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, result, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "approved",
            "resolution_note": "اصلاح نمره",
            "new_score": 40,
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(result)
    db_session.refresh(objection)

    assert objection.status == ObjectionStatus.APPROVED
    assert result.score == 40
    assert result.is_passed is False
    assert result.notification_sent is False


def test_review_rejects_negative_score(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, result, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "approved",
            "resolution_note": "نمره نامعتبر",
            "new_score": -1,
        },
        headers=headers,
    )

    assert response.status_code == 400

    db_session.refresh(result)
    db_session.refresh(objection)

    assert result.score == 50
    assert objection.status == ObjectionStatus.PENDING


def test_review_rejects_score_above_exam_total(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, result, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "approved",
            "resolution_note": "نمره نامعتبر",
            "new_score": 101,
        },
        headers=headers,
    )

    assert response.status_code == 400

    db_session.refresh(result)
    db_session.refresh(objection)

    assert result.score == 50
    assert objection.status == ObjectionStatus.PENDING


def test_non_approved_status_does_not_change_score_even_with_new_score(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, result, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "rejected",
            "resolution_note": "اعتراض رد شد",
            "new_score": 90,
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(result)
    db_session.refresh(objection)

    assert objection.status == ObjectionStatus.REJECTED
    assert result.score == 50
    assert result.is_passed is False
    assert result.notification_sent is True


def test_review_creates_audit_log(
    client,
    db_session,
    super_admin_token,
):
    _, _, _, _, objection = create_objection_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "rejected",
            "resolution_note": "ثبت در لاگ",
        },
        headers=headers,
    )

    assert response.status_code == 200

    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "objection_reviewed",
            AuditLog.target_id == str(objection.id),
        )
        .all()
    )

    assert len(logs) == 1


def test_observer_cannot_review_objection(
    client,
    db_session,
):
    _, _, _, _, objection = create_objection_data(db_session)

    observer = Admin(
        username=f"observer_{uuid.uuid4().hex[:8]}",
        full_name="Observer Admin",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.OBSERVER,
        is_active=True,
    )

    db_session.add(observer)
    db_session.commit()

    headers = login_admin(client, observer.username)

    response = client.post(
        f"/api/objections/{objection.id}/review",
        json={
            "status": "rejected",
            "resolution_note": "عدم دسترسی",
        },
        headers=headers,
    )

    assert response.status_code == 403
