from datetime import datetime, timezone

from app.models.audit import AuditLog


def create_audit_log(
    db_session,
    action="user_created",
    target_type="user",
):
    log = AuditLog(
        action=action,
        target_type=target_type,
        target_id="test-target-1",
        actor_type="admin",
        actor_id="test-admin-1",
        previous_value=None,
       new_value='{"test": true}',
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


def test_list_audit_logs_without_filters(client, super_admin_token, db_session):
    create_audit_log(db_session)
    create_audit_log(
        db_session,
        action="exam_created",
        target_type="exam",
    )

    response = client.get(
        "/api/audit-logs",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 3


def test_list_audit_logs_filter_by_action(
    client,
    super_admin_token,
    db_session,
):
    create_audit_log(db_session, action="user_created")
    create_audit_log(db_session, action="exam_created")

    response = client.get(
        "/api/audit-logs?action=user_created",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["action"] == "user_created"


def test_list_audit_logs_filter_by_target_type(
    client,
    super_admin_token,
    db_session,
):
    create_audit_log(
        db_session,
        action="user_created",
        target_type="user",
    )
    create_audit_log(
        db_session,
        action="exam_created",
        target_type="exam",
    )

    response = client.get(
        "/api/audit-logs?target_type=exam",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["target_type"] == "exam"


def test_list_audit_logs_filter_by_action_and_target_type(
    client,
    super_admin_token,
    db_session,
):
    create_audit_log(
        db_session,
        action="user_created",
        target_type="user",
    )
    create_audit_log(
        db_session,
        action="user_created",
        target_type="exam",
    )
    create_audit_log(
        db_session,
        action="exam_created",
        target_type="exam",
    )

    response = client.get(
        "/api/audit-logs?action=user_created&target_type=exam",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["action"] == "user_created"
    assert data[0]["target_type"] == "exam"


def test_list_audit_logs_custom_limit(
    client,
    super_admin_token,
    db_session,
):
    for index in range(5):
        create_audit_log(
            db_session,
            action=f"action_{index}",
            target_type="user",
        )

    response = client.get(
        "/api/audit-logs?limit=2",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
def test_log_action_without_commit(db_session):
    from app.core.audit import log_action

    entry = log_action(
        db_session,
        action="test_no_commit",
        actor_type="system",
        new_value="commit_false",
        commit=False,
    )

    assert entry is not None
    assert entry.action == "test_no_commit"
    assert entry in db_session
