from app.models.admin import Admin, AdminRole
from app.core.security import hash_password


def create_admin(
    db_session,
    username="test_admin",
    full_name="Test Admin",
    role=AdminRole.OBSERVER,
    is_active=True,
):
    admin = Admin(
        username=username,
        full_name=full_name,
        hashed_password=hash_password("StrongPass123"),
        role=role,
        is_active=is_active,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


def test_list_admins(client, db_session, super_admin_token):
    create_admin(
        db_session,
        username="list_test_admin",
        full_name="List Test Admin",
        role=AdminRole.OBSERVER,
    )

    response = client.get(
        "/api/admins",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert any(
        item["username"] == "list_test_admin"
        for item in data
    )


def test_create_admin(client, db_session, super_admin_token):
    payload = {
        "username": "new_admin",
        "full_name": "New Admin",
        "password": "NewStrongPass123",
        "role": "observer",
    }

    response = client.post(
        "/api/admins",
        json=payload,
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == "new_admin"
    assert data["full_name"] == "New Admin"
    assert data["role"] == "observer"
    assert data["is_active"] is True
    assert "hashed_password" not in data

    created = (
        db_session.query(Admin)
        .filter(Admin.username == "new_admin")
        .first()
    )

    assert created is not None
    assert created.hashed_password != "NewStrongPass123"


def test_create_admin_duplicate_username(
    client,
    db_session,
    super_admin_token,
):
    create_admin(
        db_session,
        username="duplicate_admin",
        full_name="Existing Admin",
        role=AdminRole.OBSERVER,
    )

    payload = {
        "username": "duplicate_admin",
        "full_name": "Another Admin",
        "password": "AnotherStrongPass123",
        "role": "observer",
    }

    response = client.post(
        "/api/admins",
        json=payload,
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 400
    assert "این نام کاربری قبلاً استفاده شده است" in response.json()["detail"]


def test_get_my_profile(
    client,
    db_session,
    super_admin_token,
):
    response = client.get(
        "/api/admins/me",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == "admin_test"
    assert data["full_name"] == "Test Admin"
    assert data["role"] == "super_admin"
    assert data["is_active"] is True


def test_update_admin_not_found(
    client,
    db_session,
    super_admin_token,
):
    import uuid

    missing_id = uuid.uuid4()

    response = client.patch(
        f"/api/admins/{missing_id}",
        json={
            "full_name": "Updated Name",
        },
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 404
    assert "ادمین یافت نشد" in response.json()["detail"]


def test_update_admin_fields(
    client,
    db_session,
    super_admin_token,
):
    target = create_admin(
        db_session,
        username="target_admin",
        full_name="Old Name",
        role=AdminRole.OBSERVER,
        is_active=True,
    )

    payload = {
        "full_name": "Updated Name",
        "role": "exam_manager",
        "is_active": False,
    }

    response = client.patch(
        f"/api/admins/{target.id}",
        json=payload,
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(target.id)
    assert data["username"] == "target_admin"
    assert data["full_name"] == "Updated Name"
    assert data["role"] == "exam_manager"
    assert data["is_active"] is False


def test_update_admin_with_new_password(
    client,
    db_session,
    super_admin_token,
):
    target = create_admin(
        db_session,
        username="password_target",
        full_name="Password Target",
        role=AdminRole.OBSERVER,
    )

    old_hash = target.hashed_password

    payload = {
        "new_password": "BrandNewStrongPass123",
    }

    response = client.patch(
        f"/api/admins/{target.id}",
        json=payload,
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == "password_target"

    db_session.refresh(target)

    assert target.hashed_password != old_hash
    assert target.hashed_password != "BrandNewStrongPass123"


def test_update_admin_single_field(
    client,
    db_session,
    super_admin_token,
):
    target = create_admin(
        db_session,
        username="single_field_target",
        full_name="Original Name",
        role=AdminRole.OBSERVER,
        is_active=True,
    )

    response = client.patch(
        f"/api/admins/{target.id}",
        json={
            "full_name": "Only Name Changed",
        },
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["full_name"] == "Only Name Changed"
    assert data["role"] == "observer"
    assert data["is_active"] is True
