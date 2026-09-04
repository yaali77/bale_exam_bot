import pytest
from datetime import date

from app.bot.handlers.registration import (
    _pending_registration,
    handle_contact,
    handle_national_code_input,
    handle_start,
)
from app.models.appearance import AppearanceSettings
from app.models.user import User, UserStatus
from app.core.security import validate_national_code


VALID_NATIONAL_CODE = "1234567891"


def create_user(
    db_session,
    bale_user_id,
    national_code=VALID_NATIONAL_CODE,
    phone_number=None,
    status=UserStatus.ACTIVE,
    first_name="Test",
):
    user = User(
        bale_user_id=bale_user_id,
        phone_number=phone_number or f"0912{bale_user_id:07d}",
        national_code=national_code,
        first_name=first_name,
        last_name="User",
        status=status,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def sent_messages(monkeypatch):
    messages = []
    contacts = []

    async def fake_send_message(chat_id, text):
        messages.append((chat_id, text))

    async def fake_request_contact_keyboard(chat_id, text):
        contacts.append((chat_id, text))

    monkeypatch.setattr(
        "app.bot.handlers.registration.bale_client.send_message",
        fake_send_message,
    )
    monkeypatch.setattr(
        "app.bot.handlers.registration.bale_client.request_contact_keyboard",
        fake_request_contact_keyboard,
    )

    return messages, contacts


@pytest.fixture(autouse=True)
def clear_pending_registration():
    _pending_registration.clear()
    yield
    _pending_registration.clear()


@pytest.mark.anyio
async def test_handle_start_new_user_requests_contact(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    await handle_start(
        db_session,
        bale_user_id=1001,
        chat_id=2001,
    )

    assert messages == []
    assert len(contacts) == 1
    assert contacts[0][0] == 2001
    assert 1001 in _pending_registration
    assert _pending_registration[1001]["step"] == "awaiting_contact"


@pytest.mark.anyio
async def test_handle_start_new_user_uses_custom_welcome_message(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    appearance = AppearanceSettings(
        welcome_message="پیام خوش‌آمدگویی اختصاصی"
    )
    db_session.add(appearance)
    db_session.commit()

    await handle_start(
        db_session,
        bale_user_id=1002,
        chat_id=2002,
    )

    assert len(contacts) == 1
    assert "پیام خوش‌آمدگویی اختصاصی" in contacts[0][1]


@pytest.mark.anyio
async def test_handle_start_disabled_user_sends_error_message(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    create_user(
        db_session,
        bale_user_id=1003,
        status=UserStatus.DISABLED,
    )

    await handle_start(
        db_session,
        bale_user_id=1003,
        chat_id=2003,
    )

    assert len(messages) == 1
    assert contacts == []


@pytest.mark.anyio
async def test_handle_start_disabled_user_uses_custom_error_message(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    appearance = AppearanceSettings(
        error_message="خطای اختصاصی حساب"
    )
    db_session.add(appearance)
    db_session.commit()

    create_user(
        db_session,
        bale_user_id=1004,
        status=UserStatus.DISABLED,
    )

    await handle_start(
        db_session,
        bale_user_id=1004,
        chat_id=2004,
    )

    assert messages == [(2004, "خطای اختصاصی حساب")]
    assert contacts == []


@pytest.mark.anyio
async def test_handle_start_existing_active_user_sends_welcome(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    create_user(
        db_session,
        bale_user_id=1005,
        first_name="علی",
    )

    await handle_start(
        db_session,
        bale_user_id=1005,
        chat_id=2005,
    )

    assert len(messages) == 1
    assert messages[0][0] == 2005
    assert "علی" in messages[0][1]
    assert contacts == []


@pytest.mark.anyio
async def test_handle_start_existing_user_without_first_name(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    create_user(
        db_session,
        bale_user_id=1006,
        first_name=None,
    )

    await handle_start(
        db_session,
        bale_user_id=1006,
        chat_id=2006,
    )

    assert len(messages) == 1
    assert messages[0][0] == 2006
    assert contacts == []


@pytest.mark.anyio
async def test_handle_contact_rejects_contact_from_another_user(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    await handle_contact(
        db_session,
        bale_user_id=1007,
        chat_id=2007,
        phone_number="+989121234567",
        contact_user_id=9999,
    )

    assert len(messages) == 1
    assert contacts == []
    assert 1007 not in _pending_registration


@pytest.mark.anyio
async def test_handle_contact_rejects_already_registered_phone(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    create_user(
        db_session,
        bale_user_id=1008,
        phone_number="09121234567",
    )

    _pending_registration[2008] = {
        "step": "awaiting_contact"
    }

    await handle_contact(
        db_session,
        bale_user_id=2008,
        chat_id=2008,
        phone_number="09121234567",
        contact_user_id=2008,
    )

    assert len(messages) == 1
    assert "ثبت" in messages[0][1]
    assert 2008 not in _pending_registration
    assert contacts == []


@pytest.mark.anyio
async def test_handle_contact_normalizes_iranian_phone_number(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    await handle_contact(
        db_session,
        bale_user_id=1009,
        chat_id=2009,
        phone_number="+989121234567",
        contact_user_id=1009,
    )

    assert len(messages) == 1
    assert contacts == []

    assert _pending_registration[1009] == {
        "step": "awaiting_national_code",
        "phone_number": "09121234567",
    }


@pytest.mark.anyio
async def test_handle_contact_keeps_non_iranian_format_unchanged(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    await handle_contact(
        db_session,
        bale_user_id=1010,
        chat_id=2010,
        phone_number="09129876543",
        contact_user_id=1010,
    )

    assert len(messages) == 1
    assert _pending_registration[1010]["step"] == "awaiting_national_code"
    assert _pending_registration[1010]["phone_number"] == "09129876543"


@pytest.mark.anyio
async def test_handle_national_code_without_registration_state_delegates_to_query(
    db_session,
    monkeypatch,
    sent_messages,
):
    messages, contacts = sent_messages
    called = []

    async def fake_handle_result_inquiry(
        db,
        bale_user_id,
        chat_id,
        national_code,
    ):
        called.append(
            (db, bale_user_id, chat_id, national_code)
        )

    monkeypatch.setattr(
        "app.bot.handlers.query.handle_result_inquiry",
        fake_handle_result_inquiry,
    )

    await handle_national_code_input(
        db_session,
        bale_user_id=1011,
        chat_id=2011,
        text="  1234567891  ",
    )

    assert len(called) == 1
    assert called[0][1:] == (
        1011,
        2011,
        "1234567891",
    )
    assert messages == []
    assert contacts == []


@pytest.mark.anyio
async def test_handle_national_code_with_wrong_state_delegates_to_query(
    db_session,
    monkeypatch,
    sent_messages,
):
    messages, contacts = sent_messages
    called = []

    async def fake_handle_result_inquiry(
        db,
        bale_user_id,
        chat_id,
        national_code,
    ):
        called.append(
            (bale_user_id, chat_id, national_code)
        )

    monkeypatch.setattr(
        "app.bot.handlers.query.handle_result_inquiry",
        fake_handle_result_inquiry,
    )

    _pending_registration[1012] = {
        "step": "awaiting_contact"
    }

    await handle_national_code_input(
        db_session,
        bale_user_id=1012,
        chat_id=2012,
        text="1234567891",
    )

    assert called == [
        (1012, 2012, "1234567891")
    ]
    assert messages == []
    assert contacts == []


@pytest.mark.anyio
async def test_handle_national_code_rejects_invalid_code(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    _pending_registration[1013] = {
        "step": "awaiting_national_code",
        "phone_number": "09121234567",
    }

    await handle_national_code_input(
        db_session,
        bale_user_id=1013,
        chat_id=2013,
        text="1111111111",
    )

    assert len(messages) == 1
    assert "کد ملی" in messages[0][1]
    assert 1013 in _pending_registration
    assert contacts == []


@pytest.mark.anyio
async def test_handle_national_code_rejects_duplicate_national_code(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    create_user(
        db_session,
        bale_user_id=1014,
        national_code=VALID_NATIONAL_CODE,
    )

    _pending_registration[2014] = {
        "step": "awaiting_national_code",
        "phone_number": "09121234568",
    }

    await handle_national_code_input(
        db_session,
        bale_user_id=2014,
        chat_id=2014,
        text=VALID_NATIONAL_CODE,
    )

    assert len(messages) == 1
    assert "قبلاً" in messages[0][1]
    assert 2014 not in _pending_registration
    assert contacts == []


@pytest.mark.anyio
async def test_handle_national_code_registers_new_user(
    db_session,
    sent_messages,
):
    messages, contacts = sent_messages

    _pending_registration[1015] = {
        "step": "awaiting_national_code",
        "phone_number": "09121234567",
    }

    await handle_national_code_input(
        db_session,
        bale_user_id=1015,
        chat_id=2015,
        text=f"  {VALID_NATIONAL_CODE}  ",
    )

    user = (
        db_session.query(User)
        .filter(User.bale_user_id == 1015)
        .first()
    )

    assert user is not None
    assert user.phone_number == "09121234567"
    assert user.national_code == VALID_NATIONAL_CODE
    assert user.status == UserStatus.ACTIVE

    assert 1015 not in _pending_registration
    assert len(messages) == 1
    assert messages[0][0] == 2015
    assert contacts == []


@pytest.mark.anyio
async def test_handle_national_code_registration_creates_audit_log(
    db_session,
    sent_messages,
):
    from app.models.audit import AuditLog

    _pending_registration[1016] = {
        "step": "awaiting_national_code",
        "phone_number": "09121234569",
    }

    await handle_national_code_input(
        db_session,
        bale_user_id=1016,
        chat_id=2016,
        text=VALID_NATIONAL_CODE,
    )

    user = (
        db_session.query(User)
        .filter(User.bale_user_id == 1016)
        .first()
    )

    assert user is not None

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "registration")
        .first()
    )

    assert audit is not None
    assert audit.actor_type == "user"
    assert audit.target_type == "user"
    assert audit.target_id == str(user.id)