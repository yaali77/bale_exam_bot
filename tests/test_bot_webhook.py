from unittest.mock import AsyncMock

from app.bot import webhook


def base_update(text=None, contact=None):
    message = {
        "chat": {"id": 7001},
        "from": {"id": 8001},
    }

    if text is not None:
        message["text"] = text

    if contact is not None:
        message["contact"] = contact

    return {"message": message}


def test_bale_webhook_rejects_invalid_secret(client):
    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "wrong-secret"},
        json=base_update("/start"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid webhook signature"


def test_bale_webhook_returns_ok_when_message_missing(client):
    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json={},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_bale_webhook_handles_start(client, db_session, monkeypatch):
    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_start",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("/start"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001


def test_bale_webhook_handles_contact(
    client,
    db_session,
    monkeypatch,
):
    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_contact",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update(
            contact={
                "phone_number": "09121110030",
                "user_id": 9001,
            }
        ),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001

    kwargs = handler.await_args.kwargs

    assert kwargs["phone_number"] == "09121110030"
    assert kwargs["contact_user_id"] == 9001


def test_bale_webhook_handles_contact_without_user_id(
    client,
    db_session,
    monkeypatch,
):
    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_contact",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update(
            contact={
                "phone_number": "09121110031",
            }
        ),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001

    kwargs = handler.await_args.kwargs

    assert kwargs["phone_number"] == "09121110031"
    assert kwargs["contact_user_id"] == 8001


def test_bale_webhook_handles_report(
    client,
    db_session,
    monkeypatch,
):
    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_report_card_request",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("/report"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001


def test_bale_webhook_handles_objection_start(
    client,
    db_session,
    monkeypatch,
):
    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_objection_start",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("/objection"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001


def test_bale_webhook_handles_correction_start(
    client,
    db_session,
    monkeypatch,
):
    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_correction_start",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("/correction"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001


def test_bale_webhook_handles_pending_objection(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        webhook,
        "has_pending_objection",
        lambda bale_user_id: True,
    )

    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_objection_input",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("1"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001
    assert args[3] == "1"


def test_bale_webhook_handles_pending_correction(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        webhook,
        "has_pending_objection",
        lambda bale_user_id: False,
    )

    monkeypatch.setattr(
        webhook,
        "has_pending_correction",
        lambda bale_user_id: True,
    )

    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_correction_input",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("2"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001
    assert args[3] == "2"


def test_bale_webhook_handles_national_code_input(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        webhook,
        "has_pending_objection",
        lambda bale_user_id: False,
    )

    monkeypatch.setattr(
        webhook,
        "has_pending_correction",
        lambda bale_user_id: False,
    )

    handler = AsyncMock()

    monkeypatch.setattr(
        webhook,
        "handle_national_code_input",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("1234567891"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    args = handler.await_args.args

    assert args[0] is db_session
    assert args[1] == 8001
    assert args[2] == 7001
    assert args[3] == "1234567891"


def test_bale_webhook_ignores_handler_exception(
    client,
    monkeypatch,
):
    handler = AsyncMock(
        side_effect=RuntimeError("handler failure")
    )

    monkeypatch.setattr(
        webhook,
        "handle_start",
        handler,
    )

    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json=base_update("/start"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    handler.assert_awaited_once()

def test_bale_webhook_returns_ok_when_message_has_no_text(client):
    response = client.post(
        "/webhook/bale",
        headers={"X-Webhook-Secret": "test-secret"},
        json={
            "message": {
                "chat": {"id": 12345},
                "from": {"id": 67890},
            }
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
