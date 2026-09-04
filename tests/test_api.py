def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_with_wrong_password_fails(client, super_admin_token):
    response = client.post("/api/auth/login", json={"username": "admin_test", "password": "wrong"})
    assert response.status_code == 401


def test_create_exam_requires_auth(client):
    response = client.post("/api/exams", json={
        "title": "Ø¢Ø²Ù…ÙˆÙ† Ù†Ù…ÙˆÙ†Ù‡", "exam_code": "EX-001",
        "exam_date": "2026-09-01", "passing_score": "60",
    })
    assert response.status_code == 401


def test_create_and_list_exam(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    response = client.post("/api/exams", json={
        "title": "Ø¢Ø²Ù…ÙˆÙ† Ù†Ù…ÙˆÙ†Ù‡", "exam_code": "EX-001",
        "exam_date": "2026-09-01", "total_score": "100", "passing_score": "60",
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["exam_code"] == "EX-001"

    list_response = client.get("/api/exams", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_feature_toggle(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    features = client.get("/api/features", headers=headers).json()
    assert len(features) > 0

    key = features[0]["key"]
    initial_state = features[0]["is_enabled"]

    toggle_response = client.patch(f"/api/features/{key}/toggle", headers=headers)
    assert toggle_response.status_code == 200
    assert toggle_response.json()["is_enabled"] != initial_state


def test_appearance_get_default(client):
    response = client.get("/api/appearance")
    assert response.status_code == 200
    assert response.json()["primary_color"] == "#0d3b66"


def test_appearance_update_requires_auth(client):
    response = client.patch("/api/appearance", json={"system_title": "ØªØ³Øª"})
    assert response.status_code == 401


def test_appearance_update_and_reset(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    updated = client.patch("/api/appearance", json={"system_title": "Ø³Ø§Ù…Ø§Ù†Ù‡ ØªØ³Øª", "primary_color": "#112233"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["system_title"] == "Ø³Ø§Ù…Ø§Ù†Ù‡ ØªØ³Øª"
    assert updated.json()["primary_color"] == "#112233"

    reset = client.post("/api/appearance/reset", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["primary_color"] == "#0d3b66"


def test_appearance_invalid_color_rejected(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    response = client.patch("/api/appearance", json={"primary_color": "not-a-color"}, headers=headers)
    assert response.status_code == 422


def test_broadcast_immediate_creates_job(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    response = client.post("/api/notifications/broadcast", json={
        "message": "Ù¾ÛŒØ§Ù… ØªØ³Øª", "audience": "all",
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["job_id"]

    jobs = client.get("/api/notifications/jobs", headers=headers)
    assert jobs.status_code == 200
    assert len(jobs.json()) == 1
    assert jobs.json()[0]["status"] == "sent"


def test_broadcast_scheduled_creates_pending_job(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    from datetime import datetime, timedelta, timezone
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    response = client.post("/api/notifications/broadcast", json={
        "message": "Ù¾ÛŒØ§Ù… Ø²Ù…Ø§Ù†â€ŒØ¨Ù†Ø¯ÛŒâ€ŒØ´Ø¯Ù‡", "audience": "all", "schedule_at": future,
    }, headers=headers)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    jobs = client.get("/api/notifications/jobs", headers=headers).json()
    matching = [j for j in jobs if j["id"] == job_id]
    assert matching[0]["status"] == "scheduled"

    cancel = client.post(f"/api/notifications/jobs/{job_id}/cancel", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


def test_backup_status_endpoint(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    response = client.get("/api/backups", headers=headers)
    assert response.status_code == 200
    assert "backups" in response.json()


def test_feature_toggle_not_found(client, super_admin_token):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        "/api/features/non_existing_feature/toggle",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ù‚Ø§Ø¨Ù„ÛŒØª ÛŒØ§ÙØª Ù†Ø´Ø¯"


def test_feature_toggle_twice_covers_enable_and_disable(
    client,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    features = client.get(
        "/api/features",
        headers=headers,
    ).json()

    key = features[0]["key"]

    first = client.patch(
        f"/api/features/{key}/toggle",
        headers=headers,
    )
    assert first.status_code == 200

    second = client.patch(
        f"/api/features/{key}/toggle",
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["is_enabled"] is True


def test_is_feature_enabled_missing_feature(db_session):
    from app.api.routers.features import is_feature_enabled

    result = is_feature_enabled(
        db_session,
        "definitely_non_existing_feature",
    )

    assert result is True

def test_login_inactive_admin_returns_403(
    client,
    db_session,
):
    from app.models.admin import Admin, AdminRole
    from app.core.security import hash_password

    admin = Admin(
        username="inactive_login_test",
        full_name="Inactive Login Test",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SUPER_ADMIN,
        is_active=False,
    )
    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "inactive_login_test",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 403


def test_backup_status_endpoint(
    client,
    super_admin_token,
    monkeypatch,
):
    from app.api.routers import backup as backup_router

    monkeypatch.setattr(
        backup_router,
        "list_backups",
        lambda: [{"filename": "backup_test.sql", "size": 123}],
    )

    response = client.get(
        "/api/backups",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "backups": [{"filename": "backup_test.sql", "size": 123}]
    }


def test_manual_backup_endpoint(
    client,
    super_admin_token,
    monkeypatch,
):
    from app.api.routers import backup as backup_router

    called = {"value": False}

    def fake_backup():
        called["value"] = True

    monkeypatch.setattr(
        backup_router,
        "run_database_backup",
        fake_backup,
    )

    response = client.post(
        "/api/backups/run-now",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    assert "Backup" in response.json()["detail"]
    assert called["value"] is True


def test_dashboard_stats(
    client,
    super_admin_token,
):
    response = client.get(
        "/api/dashboard/stats",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_users"] >= 0
    assert data["active_users"] >= 0
    assert data["total_exams"] >= 0
    assert data["total_results"] >= 0
    assert data["unpublished_results"] >= 0
    assert data["pending_correction_requests"] >= 0
    assert data["pending_objections"] >= 0

def test_appearance_update_allows_none_colors():
    from app.schemas.appearance import AppearanceUpdate

    payload = AppearanceUpdate(
        primary_color=None,
        secondary_color=None,
        accent_color=None,
        background_color=None,
    )

    assert payload.primary_color is None
    assert payload.secondary_color is None
    assert payload.accent_color is None
    assert payload.background_color is None

def test_broadcast_future_schedule_covers_scheduler_path(
    client,
    super_admin_token,
    monkeypatch,
):
    from datetime import datetime, timedelta, timezone
    from app.api.routers import notifications as notifications_router

    scheduled = {}

    def fake_schedule(job_id, schedule_at):
        scheduled["job_id"] = job_id
        scheduled["schedule_at"] = schedule_at

    monkeypatch.setattr(
        notifications_router,
        "schedule_broadcast_job",
        fake_schedule,
    )

    future_time = datetime.now(timezone.utc) + timedelta(hours=1)

    response = client.post(
        "/api/notifications/broadcast",
        headers={
            "Authorization": f"Bearer {super_admin_token}",
        },
        json={
            "message": "Scheduled coverage test",
            "audience": "all",
            "schedule_at": future_time.isoformat(),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["recipients_count"] == 0
    assert data["sent_count"] == 0
    assert data["failed_count"] == 0
    assert scheduled["job_id"] == data["job_id"]
    assert scheduled["schedule_at"] is not None

def test_cancel_scheduled_job_not_found(client, super_admin_token):
    response = client.post(
        "/api/notifications/jobs/00000000-0000-0000-0000-000000000000/cancel",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 404


def test_cancel_non_scheduled_job_returns_400(
    client,
    db_session,
    super_admin_token,
):
    from app.models.admin import Admin
    from app.models.broadcast_job import BroadcastJob, BroadcastJobStatus

    admin = (
        db_session.query(Admin)
        .filter(Admin.username == "admin_test")
        .first()
    )

    job = BroadcastJob(
        message="Already sent",
        audience="all",
        status=BroadcastJobStatus.SENT,
        created_by_admin_id=admin.id,
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.post(
        f"/api/notifications/jobs/{job.id}/cancel",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 400
