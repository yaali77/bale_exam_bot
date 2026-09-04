import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot.client import BaleClient


@pytest.fixture
def bale_client():
    client = BaleClient()

    client._client.post = AsyncMock()
    client._client.aclose = AsyncMock()

    yield client

    # جلوگیری از هشدار مربوط به AsyncClient واقعی
    client._client = MagicMock()


@pytest.mark.asyncio
async def test_post_success(bale_client):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"ok": True, "result": {"message_id": 1}}

    bale_client._client.post.return_value = response

    result = await bale_client._post(
        "sendMessage",
        {"chat_id": 123, "text": "سلام"},
    )

    assert result == {"ok": True, "result": {"message_id": 1}}

    bale_client._client.post.assert_awaited_once_with(
        "/sendMessage",
        json={"chat_id": 123, "text": "سلام"},
    )

    response.raise_for_status.assert_called_once()
    response.json.assert_called_once()


@pytest.mark.asyncio
async def test_post_http_error_retries_and_raises(bale_client):
    request = httpx.Request("POST", "http://test/sendMessage")
    response = httpx.Response(500, request=request)

    error = httpx.HTTPStatusError(
        "server error",
        request=request,
        response=response,
    )

    bale_client._client.post.side_effect = error

    with pytest.raises(Exception) as exc_info:
        await bale_client._post(
            "sendMessage",
            {"chat_id": 123, "text": "سلام"},
        )

    assert exc_info.value.__class__.__name__ == "RetryError"
    assert bale_client._client.post.await_count == 3

    # آخرین خطای واقعی باید HTTPStatusError باشد.
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.asyncio
async def test_send_message_without_reply_markup(bale_client):
    expected = {"ok": True}

    with patch.object(
        bale_client,
        "_post",
        new=AsyncMock(return_value=expected),
    ) as mock_post:
        result = await bale_client.send_message(
            123,
            "سلام",
        )

    assert result == expected

    mock_post.assert_awaited_once_with(
        "sendMessage",
        {
            "chat_id": 123,
            "text": "سلام",
        },
    )


@pytest.mark.asyncio
async def test_send_message_with_reply_markup(bale_client):
    expected = {"ok": True}
    keyboard = {
        "keyboard": [[{"text": "ارسال شماره تماس", "request_contact": True}]],
        "resize_keyboard": True,
    }

    with patch.object(
        bale_client,
        "_post",
        new=AsyncMock(return_value=expected),
    ) as mock_post:
        result = await bale_client.send_message(
            123,
            "سلام",
            reply_markup=keyboard,
        )

    assert result == expected

    mock_post.assert_awaited_once_with(
        "sendMessage",
        {
            "chat_id": 123,
            "text": "سلام",
            "reply_markup": keyboard,
        },
    )


@pytest.mark.asyncio
async def test_send_message_http_error_logs_and_reraises(bale_client):
    request = httpx.Request("POST", "http://test/sendMessage")
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError(
        "server error",
        request=request,
        response=response,
    )

    with patch.object(
        bale_client,
        "_post",
        new=AsyncMock(side_effect=error),
    ):
        with patch("app.bot.client.logger.error") as mock_logger:
            with pytest.raises(httpx.HTTPStatusError):
                await bale_client.send_message(
                    123,
                    "سلام",
                )

    mock_logger.assert_called_once()


@pytest.mark.asyncio
async def test_send_document_success(bale_client, tmp_path):
    file_path = tmp_path / "result.txt"
    file_path.write_text("test document", encoding="utf-8")

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "ok": True,
        "result": {"document_id": "123"},
    }

    bale_client._client.post.return_value = response

    result = await bale_client.send_document(
        123,
        str(file_path),
        "کارنامه",
    )

    assert result == {
        "ok": True,
        "result": {"document_id": "123"},
    }

    bale_client._client.post.assert_awaited_once()

    args, kwargs = bale_client._client.post.await_args

    assert args[0] == "/sendDocument"
    assert kwargs["data"] == {
        "chat_id": 123,
        "caption": "کارنامه",
    }

    assert "document" in kwargs["files"]

    uploaded_file = kwargs["files"]["document"]
    assert not uploaded_file.closed

    uploaded_file.close()

    response.raise_for_status.assert_called_once()
    response.json.assert_called_once()


@pytest.mark.asyncio
async def test_send_document_default_caption(bale_client, tmp_path):
    file_path = tmp_path / "result.txt"
    file_path.write_text("test", encoding="utf-8")

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"ok": True}

    bale_client._client.post.return_value = response

    result = await bale_client.send_document(
        456,
        str(file_path),
    )

    assert result == {"ok": True}

    _, kwargs = bale_client._client.post.await_args

    assert kwargs["data"] == {
        "chat_id": 456,
        "caption": "",
    }

    kwargs["files"]["document"].close()


@pytest.mark.asyncio
async def test_send_document_http_error(bale_client, tmp_path):
    file_path = tmp_path / "result.txt"
    file_path.write_text("test", encoding="utf-8")

    request = httpx.Request("POST", "http://test/sendDocument")
    response = httpx.Response(500, request=request)

    error = httpx.HTTPStatusError(
        "server error",
        request=request,
        response=response,
    )

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = error

    bale_client._client.post.return_value = mock_response

    with pytest.raises(httpx.HTTPStatusError):
        await bale_client.send_document(
            123,
            str(file_path),
        )


@pytest.mark.asyncio
async def test_request_contact_keyboard(bale_client):
    expected = {"ok": True}

    with patch.object(
        bale_client,
        "send_message",
        new=AsyncMock(return_value=expected),
    ) as mock_send:
        result = await bale_client.request_contact_keyboard(
            123,
            "لطفاً شماره تماس خود را ارسال کنید",
        )

    assert result == expected

    mock_send.assert_awaited_once()

    args, kwargs = mock_send.await_args

    assert args[0] == 123
    assert args[1] == "لطفاً شماره تماس خود را ارسال کنید"

    keyboard = kwargs["reply_markup"]

    assert keyboard["resize_keyboard"] is True
    assert keyboard["one_time_keyboard"] is True

    button = keyboard["keyboard"][0][0]

    assert button["request_contact"] is True
    assert "text" in button


@pytest.mark.asyncio
async def test_set_webhook(bale_client):
    expected = {"ok": True}

    with patch.object(
        bale_client,
        "_post",
        new=AsyncMock(return_value=expected),
    ) as mock_post:
        result = await bale_client.set_webhook()

    assert result == expected

    mock_post.assert_awaited_once()

    args, kwargs = mock_post.await_args

    assert args[0] == "setWebhook"
    assert "url" in args[1]
    assert kwargs == {}


@pytest.mark.asyncio
async def test_close(bale_client):
    await bale_client.close()

    bale_client._client.aclose.assert_awaited_once()