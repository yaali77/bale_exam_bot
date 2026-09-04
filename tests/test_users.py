import uuid

from app.models.user import User, UserStatus
from app.core.security import hash_password


def create_user(
    db_session,
    bale_user_id=100001,
    phone_number="09120000001",
    national_code="1234567891",
    first_name="علی",
    last_name="کرمی",
    status=UserStatus.ACTIVE,
):
    user = User(
        bale_user_id=bale_user_id,
        phone_number=phone_number,
        national_code=national_code,
        first_name=first_name,
        last_name=last_name,
        status=status,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


def test_list_users_without_search(
    client,
    db_session,
    super_admin_token,
):
    create_user(
        db_session,
        bale_user_id=100001,
        phone_number="09120000001",
        national_code="1234567891",
        first_name="علی",
        last_name="کرمی",
    )

    create_user(
        db_session,
        bale_user_id=100002,
        phone_number="09120000002",
        national_code="1111111103",
        first_name="رضا",
        last_name="احمدی",
    )

    response = client.get(
        "/api/users",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2

    usernames = {
        item["national_code"]
        for item in data
    }

    assert "1234567891" in usernames
    assert "1111111103" in usernames


def test_list_users_search_by_national_code(
    client,
    db_session,
    super_admin_token,
):
    create_user(
        db_session,
        bale_user_id=100003,
        phone_number="09120000003",
        national_code="9876543210",
        first_name="محمد",
        last_name="رضایی",
    )

    create_user(
        db_session,
        bale_user_id=100004,
        phone_number="09120000004",
        national_code="1111111103",
        first_name="حسن",
        last_name="کریمی",
    )

    response = client.get(
        "/api/users?search=9876543210",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["national_code"] == "9876543210"


def test_list_users_search_by_phone(
    client,
    db_session,
    super_admin_token,
):
    create_user(
        db_session,
        bale_user_id=100005,
        phone_number="09123334444",
        national_code="2222222202",
        first_name="حسین",
        last_name="محمدی",
    )

    response = client.get(
        "/api/users?search=3334444",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["phone_number"] == "09123334444"


def test_list_users_search_by_first_name(
    client,
    db_session,
    super_admin_token,
):
    create_user(
        db_session,
        bale_user_id=100006,
        phone_number="09123335555",
        national_code="3333333303",
        first_name="مهدی",
        last_name="اکبری",
    )

    response = client.get(
        "/api/users?search=مهدی",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["first_name"] == "مهدی"


def test_list_users_search_by_last_name(
    client,
    db_session,
    super_admin_token,
):
    create_user(
        db_session,
        bale_user_id=100007,
        phone_number="09123336666",
        national_code="4444444404",
        first_name="رضا",
        last_name="نوری",
    )

    response = client.get(
        "/api/users?search=نوری",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["last_name"] == "نوری"


def test_get_user(
    client,
    db_session,
    super_admin_token,
):
    user = create_user(
        db_session,
        bale_user_id=100008,
        phone_number="09123337777",
        national_code="5555555505",
        first_name="کاربر",
        last_name="آزمایشی",
    )

    response = client.get(
        f"/api/users/{user.id}",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(user.id)
    assert data["bale_user_id"] == 100008
    assert data["phone_number"] == "09123337777"
    assert data["national_code"] == "5555555505"
    assert data["first_name"] == "کاربر"
    assert data["last_name"] == "آزمایشی"
    assert data["status"] == "active"


def test_get_user_not_found(
    client,
    db_session,
    super_admin_token,
):
    missing_id = uuid.uuid4()

    response = client.get(
        f"/api/users/{missing_id}",
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 404
    assert "کاربر" in response.json()["detail"]


def test_update_user_status(
    client,
    db_session,
    super_admin_token,
):
    user = create_user(
        db_session,
        bale_user_id=100009,
        phone_number="09123338888",
        national_code="6666666606",
        first_name="کاربر",
        last_name="فعال",
        status=UserStatus.ACTIVE,
    )

    response = client.patch(
        f"/api/users/{user.id}/status",
        json={"status": "disabled"},
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(user.id)
    assert data["status"] == "disabled"

    db_session.refresh(user)

    assert user.status == UserStatus.DISABLED


def test_update_user_status_not_found(
    client,
    db_session,
    super_admin_token,
):
    missing_id = uuid.uuid4()

    response = client.patch(
        f"/api/users/{missing_id}/status",
        json={"status": "disabled"},
        headers=auth_headers(super_admin_token),
    )

    assert response.status_code == 404
    assert "کاربر" in response.json()["detail"]

def test_user_repr():
    from app.models.user import User

    user = User(
        national_code="1234567891",
    )

    result = repr(user)

    assert "1234567891" in result
