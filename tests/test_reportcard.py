import uuid
from pathlib import Path

from app.core.security import hash_password
from app.models.admin import Admin, AdminRole
from app.models.audit import AuditLog
from app.models.report_card import ReportCard
from app.models.user import User
from app.api.routers import reportcard as reportcard_router


def create_user(
    db_session,
    bale_user_id=987650200,
    phone_number="09121110020",
    national_code="1234567820",
    first_name="Ali",
    last_name="Karami",
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


def create_report_card(
    db_session,
    user,
    report_number="RC-123456",
    verification_code="VERIFY-123456",
    pdf_path="reports/test.pdf",
    qr_path="reports/test.png",
    is_valid=True,
):
    report_card = ReportCard(
        user_id=user.id,
        report_number=report_number,
        verification_code=verification_code,
        pdf_path=pdf_path,
        qr_path=qr_path,
        is_valid=is_valid,
    )

    db_session.add(report_card)
    db_session.commit()
    db_session.refresh(report_card)

    return report_card


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


def create_admin(
    db_session,
    username,
    role=AdminRole.SUPER_ADMIN,
):
    admin = Admin(
        username=username,
        full_name="Report Card Admin",
        hashed_password=hash_password("StrongPass123"),
        role=role,
        is_active=True,
    )

    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    return admin


def test_generate_report_card_requires_auth(client, db_session):
    user = create_user(db_session)

    response = client.post(
        f"/api/users/{user.id}/report-card"
    )

    assert response.status_code == 401


def test_generate_report_card_returns_404_for_missing_user(
    client,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/users/{uuid.uuid4()}/report-card",
        headers=headers,
    )

    assert response.status_code == 404


def test_generate_or_refresh_report_card_creates_new_card(
    db_session,
    monkeypatch,
):
    user = create_user(db_session)

    monkeypatch.setattr(
        reportcard_router,
        "_generate_report_number",
        lambda national_code: "RC-NEW-001",
    )
    monkeypatch.setattr(
        reportcard_router,
        "generate_verification_code",
        lambda: "VERIFY-NEW-001",
    )
    monkeypatch.setattr(
        reportcard_router,
        "generate_qr_image",
        lambda verification_code: "reports/new_qr.png",
    )
    monkeypatch.setattr(
        reportcard_router,
        "build_report_card_pdf",
        lambda db, user, qr_path, report_number: "reports/new_card.pdf",
    )

    result = reportcard_router.generate_or_refresh_report_card(
        db_session,
        user,
    )

    assert result.id is not None
    assert result.user_id == user.id
    assert result.report_number == "RC-NEW-001"
    assert result.verification_code == "VERIFY-NEW-001"
    assert result.qr_path == "reports/new_qr.png"
    assert result.pdf_path == "reports/new_card.pdf"
    assert result.is_valid is True

    cards = (
        db_session.query(ReportCard)
        .filter(ReportCard.user_id == user.id)
        .all()
    )

    assert len(cards) == 1


def test_generate_or_refresh_report_card_refreshes_existing_card(
    db_session,
    monkeypatch,
):
    user = create_user(db_session)

    existing = create_report_card(
        db_session,
        user,
        report_number="RC-EXISTING",
        verification_code="VERIFY-EXISTING",
        pdf_path="old/card.pdf",
        qr_path="old/qr.png",
    )

    monkeypatch.setattr(
        reportcard_router,
        "generate_qr_image",
        lambda verification_code: "reports/refreshed_qr.png",
    )
    monkeypatch.setattr(
        reportcard_router,
        "build_report_card_pdf",
        lambda db, user, qr_path, report_number: "reports/refreshed_card.pdf",
    )

    result = reportcard_router.generate_or_refresh_report_card(
        db_session,
        user,
    )

    assert result.id == existing.id
    assert result.report_number == "RC-EXISTING"
    assert result.verification_code == "VERIFY-EXISTING"
    assert result.qr_path == "reports/refreshed_qr.png"
    assert result.pdf_path == "reports/refreshed_card.pdf"

    cards = (
        db_session.query(ReportCard)
        .filter(ReportCard.user_id == user.id)
        .all()
    )

    assert len(cards) == 1


def test_generate_report_card_endpoint(
    client,
    db_session,
    super_admin_token,
    monkeypatch,
):
    user = create_user(db_session)

    monkeypatch.setattr(
        reportcard_router,
        "_generate_report_number",
        lambda national_code: "RC-ENDPOINT-001",
    )
    monkeypatch.setattr(
        reportcard_router,
        "generate_verification_code",
        lambda: "VERIFY-ENDPOINT-001",
    )
    monkeypatch.setattr(
        reportcard_router,
        "generate_qr_image",
        lambda verification_code: "reports/endpoint_qr.png",
    )
    monkeypatch.setattr(
        reportcard_router,
        "build_report_card_pdf",
        lambda db, user, qr_path, report_number: "reports/endpoint.pdf",
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/users/{user.id}/report-card",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["report_number"] == "RC-ENDPOINT-001"
    assert data["pdf_path"] == "reports/endpoint.pdf"
    assert data["verification_code"] == "VERIFY-ENDPOINT-001"

    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "report_card_generated",
            AuditLog.target_id == str(user.id),
        )
        .all()
    )

    assert len(logs) == 1
    assert logs[0].new_value == "RC-ENDPOINT-001"


def test_download_report_card_requires_auth(
    client,
    db_session,
):
    user = create_user(db_session)

    response = client.get(
        f"/api/users/{user.id}/report-card/download"
    )

    assert response.status_code == 401


def test_download_report_card_returns_pdf(
    client,
    db_session,
    super_admin_token,
    tmp_path,
):
    user = create_user(db_session)

    pdf_file = tmp_path / "report_card.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    report_card = create_report_card(
        db_session,
        user,
        report_number="RC-DOWNLOAD-001",
        verification_code="VERIFY-DOWNLOAD-001",
        pdf_path=str(pdf_file),
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        f"/api/users/{user.id}/report-card/download",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-1.4")

    assert report_card.pdf_path == str(pdf_file)


def test_download_report_card_returns_404_when_missing(
    client,
    db_session,
    super_admin_token,
):
    user = create_user(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        f"/api/users/{user.id}/report-card/download",
        headers=headers,
    )

    assert response.status_code == 404


def test_download_report_card_returns_404_when_pdf_path_is_empty(
    client,
    db_session,
    super_admin_token,
):
    user = create_user(db_session)

    create_report_card(
        db_session,
        user,
        report_number="RC-NOPDF-001",
        verification_code="VERIFY-NOPDF-001",
        pdf_path=None,
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        f"/api/users/{user.id}/report-card/download",
        headers=headers,
    )

    assert response.status_code == 404


def test_verify_report_card_returns_404_for_invalid_code(
    client,
):
    response = client.get(
        "/verify/INVALID-CODE-999"
    )

    assert response.status_code == 404


def test_verify_invalidated_report_card(
    client,
    db_session,
):
    user = create_user(db_session)

    report_card = create_report_card(
        db_session,
        user,
        report_number="RC-VOID-001",
        verification_code="VERIFY-VOID-001",
        is_valid=False,
    )

    response = client.get(
        f"/verify/{report_card.verification_code}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["valid"] is False
    assert data["message"] == "این کارنامه ابطال شده است"

    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "report_card_verified",
            AuditLog.target_id == str(report_card.id),
        )
        .all()
    )

    assert len(logs) == 1
    assert logs[0].actor_type == "public"


def test_verify_valid_report_card_returns_masked_national_code(
    client,
    db_session,
):
    user = create_user(
        db_session,
        national_code="1234567820",
    )

    report_card = create_report_card(
        db_session,
        user,
        report_number="RC-VALID-001",
        verification_code="VERIFY-VALID-001",
        is_valid=True,
    )

    response = client.get(
        f"/verify/{report_card.verification_code}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["valid"] is True
    assert data["report_number"] == "RC-VALID-001"
    assert data["national_code_masked"] == "123****820"
    assert "issued_at" in data

    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "report_card_verified",
            AuditLog.target_id == str(report_card.id),
        )
        .all()
    )

    assert len(logs) == 1


def test_void_report_card_requires_delete_permission(
    client,
    db_session,
):
    user = create_user(db_session)

    report_card = create_report_card(
        db_session,
        user,
        report_number="RC-PERM-001",
        verification_code="VERIFY-PERM-001",
    )

    support = create_admin(
        db_session,
        f"report_support_{uuid.uuid4().hex[:8]}",
        AdminRole.SUPPORT,
    )

    headers = login_admin(client, support.username)

    response = client.post(
        f"/api/report-cards/{report_card.id}/void",
        headers=headers,
    )

    assert response.status_code == 403


def test_void_report_card_returns_404_for_missing_card(
    client,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/report-cards/{uuid.uuid4()}/void",
        headers=headers,
    )

    assert response.status_code == 404


def test_void_report_card_success(
    client,
    db_session,
    super_admin_token,
):
    user = create_user(db_session)

    report_card = create_report_card(
        db_session,
        user,
        report_number="RC-VOID-SUCCESS",
        verification_code="VERIFY-VOID-SUCCESS",
        is_valid=True,
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/report-cards/{report_card.id}/void",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detail"] == "کارنامه ابطال شد"

    db_session.refresh(report_card)

    assert report_card.is_valid is False

    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "report_card_voided",
            AuditLog.target_id == str(report_card.id),
        )
        .all()
    )

    assert len(logs) == 1


def test_verify_after_void_report_card_returns_invalid(
    client,
    db_session,
    super_admin_token,
):
    user = create_user(db_session)

    report_card = create_report_card(
        db_session,
        user,
        report_number="RC-VERIFY-AFTER-VOID",
        verification_code="VERIFY-AFTER-VOID",
        is_valid=True,
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    void_response = client.post(
        f"/api/report-cards/{report_card.id}/void",
        headers=headers,
    )

    assert void_response.status_code == 200

    verify_response = client.get(
        f"/verify/{report_card.verification_code}"
    )

    assert verify_response.status_code == 200

    data = verify_response.json()

    assert data["valid"] is False
    assert data["message"] == "این کارنامه ابطال شده است"
