from datetime import date
import uuid

from app.core.security import hash_password
from app.models.admin import Admin, AdminRole
from app.models.audit import AuditLog
from app.models.correction import CorrectionRequest, RequestStatus
from app.models.exam import Exam
from app.models.user import User


def create_correction_data(
    db_session,
    field_name="first_name",
    previous_value="Ali",
    requested_value="Reza",
    status=RequestStatus.PENDING,
):
    user = User(
        bale_user_id=987650101,
        phone_number="09121110002",
        national_code="1234567802",
        first_name="Ali",
        last_name="Karami",
    )

    admin = Admin(
        username=f"correction_admin_{uuid.uuid4().hex[:8]}",
        full_name="Correction Admin",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
    )

    db_session.add_all([user, admin])
    db_session.commit()

    correction = CorrectionRequest(
        user_id=user.id,
        field_name=field_name,
        previous_value=previous_value,
        requested_value=requested_value,
        user_note="درخواست اصلاح تستی",
        status=status,
    )

    db_session.add(correction)
    db_session.commit()
    db_session.refresh(correction)

    return user, admin, correction


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


def test_list_correction_requests_requires_auth(client):
    response = client.get("/api/corrections")

    assert response.status_code == 401


def test_list_correction_requests_returns_all(
    client,
    db_session,
    super_admin_token,
):
    _, _, correction = create_correction_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        "/api/corrections",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(correction.id)
    assert data[0]["field_name"] == "first_name"
    assert data[0]["requested_value"] == "Reza"
    assert data[0]["status"] == "pending"


def test_list_correction_requests_filters_by_status(
    client,
    db_session,
    super_admin_token,
):
    _, _, pending = create_correction_data(db_session)

    rejected = CorrectionRequest(
        user_id=pending.user_id,
        field_name="last_name",
        previous_value="Karami",
        requested_value="Ahmadi",
        user_note="درخواست دوم",
        status=RequestStatus.REJECTED,
    )

    db_session.add(rejected)
    db_session.commit()

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        "/api/corrections",
        params={"status": "rejected"},
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(rejected.id)
    assert data[0]["status"] == "rejected"


def test_support_can_view_corrections_but_cannot_review(
    client,
    db_session,
):
    _, _, correction = create_correction_data(db_session)

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
        "/api/corrections",
        headers=headers,
    )

    assert response.status_code == 200

    review = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "rejected",
            "admin_note": "عدم دسترسی به ویرایش",
        },
        headers=headers,
    )

    assert review.status_code == 403


def test_observer_cannot_review_correction(
    client,
    db_session,
):
    _, _, correction = create_correction_data(db_session)

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
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "rejected",
            "admin_note": "عدم دسترسی",
        },
        headers=headers,
    )

    assert response.status_code == 403


def test_review_missing_correction_returns_404(
    client,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    missing_id = uuid.uuid4()

    response = client.post(
        f"/api/corrections/{missing_id}/review",
        json={
            "status": "rejected",
            "admin_note": "درخواست پیدا نشد",
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_review_rejected_correction(
    client,
    db_session,
    super_admin_token,
):
    user, _, correction = create_correction_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "rejected",
            "admin_note": "اطلاعات قابل تأیید نیست",
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(correction)
    db_session.refresh(user)

    authenticated_admin = (
        db_session.query(Admin)
        .filter(Admin.username == "admin_test")
        .first()
    )

    assert correction.status == RequestStatus.REJECTED
    assert correction.admin_note == "اطلاعات قابل تأیید نیست"
    assert correction.reviewed_by_admin_id == authenticated_admin.id
    assert correction.reviewed_at is not None

    assert user.first_name == "Ali"


def test_review_approved_first_name_updates_user(
    client,
    db_session,
    super_admin_token,
):
    user, _, correction = create_correction_data(
        db_session,
        field_name="first_name",
        previous_value="Ali",
        requested_value="Reza",
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "approved",
            "admin_note": "نام تأیید شد",
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(user)
    db_session.refresh(correction)

    assert user.first_name == "Reza"
    assert correction.status == RequestStatus.APPROVED
    assert correction.admin_note == "نام تأیید شد"
    assert correction.reviewed_at is not None


def test_review_approved_last_name_updates_user(
    client,
    db_session,
    super_admin_token,
):
    user, _, correction = create_correction_data(
        db_session,
        field_name="last_name",
        previous_value="Karami",
        requested_value="Ahmadi",
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "approved",
            "admin_note": "نام خانوادگی تأیید شد",
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(user)
    db_session.refresh(correction)

    assert user.last_name == "Ahmadi"
    assert correction.status == RequestStatus.APPROVED
    assert correction.reviewed_at is not None


def test_review_approved_phone_number_updates_user(
    client,
    db_session,
    super_admin_token,
):
    user, _, correction = create_correction_data(
        db_session,
        field_name="phone_number",
        previous_value="09121110002",
        requested_value="09129990003",
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "approved",
            "admin_note": "شماره تلفن تأیید شد",
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(user)
    db_session.refresh(correction)

    assert user.phone_number == "09129990003"
    assert correction.status == RequestStatus.APPROVED
    assert correction.reviewed_at is not None


def test_review_approved_rejects_forbidden_field(
    client,
    db_session,
    super_admin_token,
):
    user, _, correction = create_correction_data(
        db_session,
        field_name="national_code",
        previous_value="1234567802",
        requested_value="9876543210",
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "approved",
            "admin_note": "کد ملی نباید تغییر کند",
        },
        headers=headers,
    )

    assert response.status_code == 400

    db_session.refresh(user)
    db_session.refresh(correction)

    assert user.national_code == "1234567802"
    assert correction.status == RequestStatus.PENDING
    assert correction.reviewed_by_admin_id is None
    assert correction.reviewed_at is None


def test_review_rejected_does_not_modify_user_even_for_allowed_field(
    client,
    db_session,
    super_admin_token,
):
    user, _, correction = create_correction_data(
        db_session,
        field_name="first_name",
        previous_value="Ali",
        requested_value="Reza",
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "rejected",
            "admin_note": "درخواست رد شد",
        },
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(user)
    db_session.refresh(correction)

    assert user.first_name == "Ali"
    assert correction.status == RequestStatus.REJECTED


def test_review_creates_audit_log(
    client,
    db_session,
    super_admin_token,
):
    _, _, correction = create_correction_data(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/corrections/{correction.id}/review",
        json={
            "status": "rejected",
            "admin_note": "ثبت در لاگ",
        },
        headers=headers,
    )

    assert response.status_code == 200

    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "correction_reviewed",
            AuditLog.target_id == str(correction.id),
        )
        .all()
    )

    assert len(logs) == 1
    assert logs[0].new_value == correction.requested_value
    assert logs[0].previous_value == correction.previous_value
