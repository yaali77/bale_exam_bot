from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text

from app.api.routers.monitoring import system_status


@pytest.mark.asyncio
async def test_system_status_all_ok(db_session, monkeypatch):
    response = MagicMock()
    response.status_code = 200

    mock_get = AsyncMock(return_value=response)

    monkeypatch.setattr(
        "app.api.routers.monitoring.bale_client._client.get",
        mock_get,
    )

    result = await system_status(db_session)

    assert result == {
        "database": "ok",
        "bale_bot": "ok",
    }

    mock_get.assert_awaited_once_with("/getMe")


@pytest.mark.asyncio
async def test_system_status_database_error(monkeypatch):
    db = MagicMock()

    db.execute.side_effect = Exception("database unavailable")

    response = MagicMock()
    response.status_code = 200

    monkeypatch.setattr(
        "app.api.routers.monitoring.bale_client._client.get",
        AsyncMock(return_value=response),
    )

    result = await system_status(db)

    assert result["database"] == "error: database unavailable"
    assert result["bale_bot"] == "ok"


@pytest.mark.asyncio
async def test_system_status_bale_http_error(db_session, monkeypatch):
    response = MagicMock()
    response.status_code = 500

    mock_get = AsyncMock(return_value=response)

    monkeypatch.setattr(
        "app.api.routers.monitoring.bale_client._client.get",
        mock_get,
    )

    result = await system_status(db_session)

    assert result["database"] == "ok"
    assert result["bale_bot"] == "error: HTTP 500"

    mock_get.assert_awaited_once_with("/getMe")


@pytest.mark.asyncio
async def test_system_status_bale_exception(db_session, monkeypatch):
    mock_get = AsyncMock(
        side_effect=Exception("Bale unavailable")
    )

    monkeypatch.setattr(
        "app.api.routers.monitoring.bale_client._client.get",
        mock_get,
    )

    result = await system_status(db_session)

    assert result["database"] == "ok"
    assert result["bale_bot"] == "error: Bale unavailable"


@pytest.mark.asyncio
async def test_system_status_database_and_bale_errors(monkeypatch):
    db = MagicMock()
    db.execute.side_effect = Exception("database unavailable")

    mock_get = AsyncMock(
        side_effect=Exception("Bale unavailable")
    )

    monkeypatch.setattr(
        "app.api.routers.monitoring.bale_client._client.get",
        mock_get,
    )

    result = await system_status(db)

    assert result == {
        "database": "error: database unavailable",
        "bale_bot": "error: Bale unavailable",
    }
