
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import app.api.deps as deps


def test_get_current_admin_valid_token_returns_active_admin(monkeypatch):
    admin = MagicMock()
    admin.is_active = True
    admin_id = "admin-123"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = admin

    monkeypatch.setattr(
        deps,
        "decode_access_token",
        lambda token: {"sub": admin_id},
    )

    result = deps.get_current_admin("valid-token", db)

    assert result is admin
    db.query.assert_called_once_with(deps.Admin)


def test_get_current_admin_invalid_token_raises_401(monkeypatch):
    db = MagicMock()

    monkeypatch.setattr(
        deps,
        "decode_access_token",
        lambda token: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_admin("invalid-token", db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


def test_get_current_admin_admin_not_found_raises_401(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    monkeypatch.setattr(
        deps,
        "decode_access_token",
        lambda token: {"sub": "missing-admin"},
    )

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_admin("valid-token", db)

    assert exc_info.value.status_code == 401


def test_get_current_admin_inactive_admin_raises_401(monkeypatch):
    admin = MagicMock()
    admin.is_active = False

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = admin

    monkeypatch.setattr(
        deps,
        "decode_access_token",
        lambda token: {"sub": "inactive-admin"},
    )

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_admin("valid-token", db)

    assert exc_info.value.status_code == 401


def test_get_current_admin_missing_sub_raises_401(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    monkeypatch.setattr(
        deps,
        "decode_access_token",
        lambda token: {},
    )

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_admin("valid-token", db)

    assert exc_info.value.status_code == 401


def test_require_permission_allowed_returns_admin(monkeypatch):
    admin = MagicMock()
    admin.role = MagicMock()

    monkeypatch.setattr(
        deps,
        "has_permission",
        lambda role, permission: True,
    )

    checker = deps.require_permission("view")
    result = checker(admin)

    assert result is admin


def test_require_permission_denied_raises_403(monkeypatch):
    admin = MagicMock()
    admin.role = MagicMock()

    monkeypatch.setattr(
        deps,
        "has_permission",
        lambda role, permission: False,
    )

    checker = deps.require_permission("settings")

    with pytest.raises(HTTPException) as exc_info:
        checker(admin)

    assert exc_info.value.status_code == 403
