from unittest.mock import AsyncMock

from app.bot.handlers import correction as correction_handler
from app.models.correction import CorrectionRequest
from app.models.feature import FeatureFlag
from app.models.user import User


def create_user(
    db_session,
    bale_user_id=987650300,
    phone_number="09121110030",
    national_code="1234567830",
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


def clear_pending():
    correction_handler._pending_correction.clear()


def test_is_feature_enabled_returns_true_when_feature_missing(
    db_session,
):
    result = correction_handler._is_feature_enabled(
        db_session,
        "correction_request",
    )

    assert result is True


def test_is_feature_enabled_returns_feature_value(
    db_session,
):
    feature = FeatureFlag(
            key="correction_request",
            display_name="درخواست اصلاح اطلاعات",
            is_enabled=False,
        )

    db_session.add(feature)
    db_session.commit()

    result = correction_handler._is_feature_enabled(
        db_session,
        "correction_request",
    )

    assert result is False


async def test_handle_correction_start_when_feature_disabled(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        correction_handler,
        "_is_feature_enabled",
        lambda db, key: False,
    )

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    clear_pending()

    await correction_handler.handle_correction_start(
        db_session,
        bale_user_id=987650301,
        chat_id=5001,
    )

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 5001
    assert "غیرفعال" in args[1]

    assert correction_handler.has_pending_correction(
        987650301
    ) is False


async def test_handle_correction_start_when_user_not_found(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        correction_handler,
        "_is_feature_enabled",
        lambda db, key: True,
    )

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    clear_pending()

    await correction_handler.handle_correction_start(
        db_session,
        bale_user_id=987650302,
        chat_id=5002,
    )

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 5002
    assert "/start" in args[1]

    assert correction_handler.has_pending_correction(
        987650302
    ) is False


async def test_handle_correction_start_for_existing_user(
    db_session,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=987650303,
    )

    monkeypatch.setattr(
        correction_handler,
        "_is_feature_enabled",
        lambda db, key: True,
    )

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    clear_pending()

    await correction_handler.handle_correction_start(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=5003,
    )

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 5003
    assert "نام" in args[1]
    assert "نام خانوادگی" in args[1]
    assert "شماره تلفن" in args[1]

    assert correction_handler.has_pending_correction(
        user.bale_user_id
    ) is True

    state = correction_handler._pending_correction[
        user.bale_user_id
    ]

    assert state["step"] == "choosing_field"
    assert state["fields"] == [
        "first_name",
        "last_name",
        "phone_number",
    ]


async def test_handle_correction_input_without_pending_state(
    db_session,
):
    clear_pending()

    result = await correction_handler.handle_correction_input(
        db_session,
        bale_user_id=987650304,
        chat_id=5004,
        text="1",
    )

    assert result is False


async def test_handle_correction_input_invalid_field_selection(
    db_session,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=987650305,
    )

    clear_pending()

    correction_handler._pending_correction[user.bale_user_id] = {
        "step": "choosing_field",
        "fields": [
            "first_name",
            "last_name",
            "phone_number",
        ],
    }

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    result = await correction_handler.handle_correction_input(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=5005,
        text="99",
    )

    assert result is True

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 5005
    assert "نامعتبر" in args[1]

    state = correction_handler._pending_correction[
        user.bale_user_id
    ]

    assert state["step"] == "choosing_field"


async def test_handle_correction_input_non_numeric_field_selection(
    db_session,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=987650306,
    )

    clear_pending()

    correction_handler._pending_correction[user.bale_user_id] = {
        "step": "choosing_field",
        "fields": [
            "first_name",
            "last_name",
            "phone_number",
        ],
    }

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    result = await correction_handler.handle_correction_input(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=5006,
        text="abc",
    )

    assert result is True

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 5006
    assert "نامعتبر" in args[1]


async def test_handle_correction_input_valid_field_selection(
    db_session,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=987650307,
    )

    clear_pending()

    correction_handler._pending_correction[user.bale_user_id] = {
        "step": "choosing_field",
        "fields": [
            "first_name",
            "last_name",
            "phone_number",
        ],
    }

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    result = await correction_handler.handle_correction_input(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=5007,
        text="2",
    )

    assert result is True

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 5007
    assert "نام خانوادگی" in args[1]

    state = correction_handler._pending_correction[
        user.bale_user_id
    ]

    assert state["step"] == "awaiting_value"
    assert state["field"] == "last_name"


async def test_handle_correction_input_creates_correction_request(
    db_session,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=987650308,
        first_name="Ali",
    )

    clear_pending()

    correction_handler._pending_correction[user.bale_user_id] = {
        "step": "awaiting_value",
        "fields": [
            "first_name",
            "last_name",
            "phone_number",
        ],
        "field": "first_name",
    }

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    result = await correction_handler.handle_correction_input(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=5008,
        text="  Reza  ",
    )

    assert result is True

    request = (
        db_session.query(CorrectionRequest)
        .filter(
            CorrectionRequest.user_id == user.id,
        )
        .first()
    )

    assert request is not None
    assert request.field_name == "first_name"
    assert request.previous_value == "Ali"
    assert request.requested_value == "Reza"

    assert send_message.await_count == 1

    args = send_message.await_args.args

    assert args[0] == 5008
    assert "ثبت شد" in args[1]

    assert correction_handler.has_pending_correction(
        user.bale_user_id
    ) is False


async def test_handle_correction_input_creates_phone_correction(
    db_session,
    monkeypatch,
):
    user = create_user(
        db_session,
        bale_user_id=987650309,
        phone_number="09121110030",
    )

    clear_pending()

    correction_handler._pending_correction[user.bale_user_id] = {
        "step": "awaiting_value",
        "fields": [
            "first_name",
            "last_name",
            "phone_number",
        ],
        "field": "phone_number",
    }

    send_message = AsyncMock()

    monkeypatch.setattr(
        correction_handler.bale_client,
        "send_message",
        send_message,
    )

    result = await correction_handler.handle_correction_input(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=5009,
        text="  09129990030  ",
    )

    assert result is True

    request = (
        db_session.query(CorrectionRequest)
        .filter(
            CorrectionRequest.user_id == user.id,
            CorrectionRequest.field_name == "phone_number",
        )
        .first()
    )

    assert request is not None
    assert request.previous_value == "09121110030"
    assert request.requested_value == "09129990030"

    assert correction_handler.has_pending_correction(
        user.bale_user_id
    ) is False


async def test_handle_correction_input_returns_false_for_unknown_step(
    db_session,
):
    user = create_user(
        db_session,
        bale_user_id=987650310,
    )

    clear_pending()

    correction_handler._pending_correction[user.bale_user_id] = {
        "step": "unknown_step",
        "fields": [
            "first_name",
            "last_name",
            "phone_number",
        ],
    }

    result = await correction_handler.handle_correction_input(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=5010,
        text="anything",
    )

    assert result is False

    assert correction_handler.has_pending_correction(
        user.bale_user_id
    ) is True


def test_has_pending_correction_returns_true_and_false():
    clear_pending()

    assert correction_handler.has_pending_correction(
        987650311
    ) is False

    correction_handler._pending_correction[987650311] = {
        "step": "choosing_field"
    }

    assert correction_handler.has_pending_correction(
        987650311
    ) is True

    clear_pending()
