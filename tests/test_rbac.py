from app.models.admin import AdminRole, ROLE_PERMISSIONS, has_permission


def test_all_admin_roles_exist():
    expected_roles = {
        "super_admin",
        "system_manager",
        "exam_manager",
        "score_operator",
        "user_operator",
        "support",
        "observer",
    }

    actual_roles = {role.value for role in AdminRole}

    assert actual_roles == expected_roles


def test_permission_matrix():
    expected_matrix = {
        AdminRole.SUPER_ADMIN: {
            "view", "create", "edit", "delete",
            "publish", "report", "settings",
        },
        AdminRole.SYSTEM_MANAGER: {
            "view", "create", "edit", "delete",
            "publish", "report", "settings",
        },
        AdminRole.EXAM_MANAGER: {
            "view", "create", "edit",
            "publish", "report",
        },
        AdminRole.SCORE_OPERATOR: {
            "view", "create", "edit",
        },
        AdminRole.USER_OPERATOR: {
            "view", "create", "edit",
        },
        AdminRole.SUPPORT: {
            "view", "report",
        },
        AdminRole.OBSERVER: {
            "view",
        },
    }

    assert ROLE_PERMISSIONS == expected_matrix

    for role, permissions in expected_matrix.items():
        for permission in {
            "view", "create", "edit", "delete",
            "publish", "report", "settings",
        }:
            assert has_permission(role, permission) == (
                permission in permissions
            )


def test_unknown_permission_is_denied():
    for role in AdminRole:
        assert has_permission(role, "unknown_permission") is False

def test_score_operator_cannot_publish_via_publish_endpoint(
    client,
    db_session,
):
    from datetime import date
    import uuid

    from app.core.security import hash_password
    from app.models.admin import Admin
    from app.models.exam import Exam
    from app.models.result import Result, ResultStatus
    from app.models.user import User

    admin = Admin(
        username="score_operator_publish_test",
        full_name="Score Operator Publish Test",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SCORE_OPERATOR,
        is_active=True,
    )

    user = User(
        bale_user_id=987654321,
        phone_number="09120000001",
        national_code="1234567890",
        first_name="Test",
        last_name="User",
    )

    exam = Exam(
        title="RBAC Publish Test",
        exam_code=f"RBAC-{uuid.uuid4().hex[:8]}",
        exam_date=date(2026, 9, 3),
        total_score=100,
        passing_score=60,
    )

    db_session.add_all([admin, user, exam])
    db_session.commit()

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=75,
        is_passed=True,
        status=ResultStatus.RECORDED,
        recorded_by_admin_id=admin.id,
    )

    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "score_operator_publish_test",
            "password": "StrongPass123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/results/{result.id}/publish",
        headers=headers,
    )

    assert response.status_code == 403

    db_session.refresh(result)
    assert result.status == ResultStatus.RECORDED

def test_score_operator_cannot_publish_via_update_endpoint(
    client,
    db_session,
):
    from datetime import date
    import uuid

    from app.core.security import hash_password
    from app.models.admin import Admin
    from app.models.exam import Exam
    from app.models.result import Result, ResultStatus
    from app.models.user import User

    admin = Admin(
        username="score_operator_update_test",
        full_name="Score Operator Update Test",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SCORE_OPERATOR,
        is_active=True,
    )

    user = User(
        bale_user_id=987654322,
        phone_number="09120000002",
        national_code="1234567891",
        first_name="Test",
        last_name="User",
    )

    exam = Exam(
        title="RBAC Update Publish Test",
        exam_code=f"RBAC-UPD-{uuid.uuid4().hex[:8]}",
        exam_date=date(2026, 9, 3),
        total_score=100,
        passing_score=60,
    )

    db_session.add_all([admin, user, exam])
    db_session.commit()

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=75,
        is_passed=True,
        status=ResultStatus.RECORDED,
        recorded_by_admin_id=admin.id,
    )

    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "score_operator_update_test",
            "password": "StrongPass123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "status": "published",
            "change_reason": "Unauthorized publish attempt",
        },
        headers=headers,
    )

    assert response.status_code == 403

    db_session.refresh(result)
    assert result.status == ResultStatus.RECORDED

def test_score_operator_can_edit_score(
    client,
    db_session,
):
    from datetime import date
    import uuid

    from app.core.security import hash_password
    from app.models.admin import Admin
    from app.models.exam import Exam
    from app.models.result import Result, ResultStatus
    from app.models.user import User

    admin = Admin(
        username="score_operator_edit_test",
        full_name="Score Operator Edit Test",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SCORE_OPERATOR,
        is_active=True,
    )

    user = User(
        bale_user_id=987654323,
        phone_number="09120000003",
        national_code="1234567892",
        first_name="Test",
        last_name="User",
    )

    exam = Exam(
        title="RBAC Score Edit Test",
        exam_code=f"RBAC-EDIT-{uuid.uuid4().hex[:8]}",
        exam_date=date(2026, 9, 3),
        total_score=100,
        passing_score=60,
    )

    db_session.add_all([admin, user, exam])
    db_session.commit()

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=75,
        is_passed=True,
        status=ResultStatus.RECORDED,
        recorded_by_admin_id=admin.id,
    )

    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "score_operator_edit_test",
            "password": "StrongPass123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": 80,
            "change_reason": "Corrected score",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert float(response.json()["score"]) == 80

    db_session.refresh(result)
    assert result.score == 80
    assert result.status == ResultStatus.RECORDED

def test_score_operator_cannot_void_result(
    client,
    db_session,
):
    from datetime import date
    import uuid

    from app.core.security import hash_password
    from app.models.admin import Admin
    from app.models.exam import Exam
    from app.models.result import Result, ResultStatus
    from app.models.user import User

    admin = Admin(
        username="score_operator_void_test",
        full_name="Score Operator Void Test",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SCORE_OPERATOR,
        is_active=True,
    )

    user = User(
        bale_user_id=987654324,
        phone_number="09120000004",
        national_code="1234567893",
        first_name="Test",
        last_name="User",
    )

    exam = Exam(
        title="RBAC Void Test",
        exam_code=f"RBAC-VOID-{uuid.uuid4().hex[:8]}",
        exam_date=date(2026, 9, 3),
        total_score=100,
        passing_score=60,
    )

    db_session.add_all([admin, user, exam])
    db_session.commit()

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=75,
        is_passed=True,
        status=ResultStatus.RECORDED,
        recorded_by_admin_id=admin.id,
    )

    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "score_operator_void_test",
            "password": "StrongPass123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/results/{result.id}/void",
        params={"reason": "Unauthorized void attempt"},
        headers=headers,
    )

    assert response.status_code == 403

    db_session.refresh(result)

    assert result.status == ResultStatus.RECORDED
    assert result.change_reason is None


def test_admin_repr():
    from app.models.admin import Admin, AdminRole

    admin = Admin(
        username="repr_admin",
        role=AdminRole.SUPER_ADMIN,
    )

    result = repr(admin)

    assert "repr_admin" in result
    assert "SUPER_ADMIN" in result
