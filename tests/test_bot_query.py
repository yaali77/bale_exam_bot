from datetime import date, datetime, timezone

import pytest

from app.bot.handlers.query import handle_result_inquiry
from app.models.exam import Exam
from app.models.result import Result, ResultStatus
from app.models.user import User, UserStatus


VALID_NATIONAL_CODE = "1234567891"


def create_user(
    db_session,
    bale_user_id: int,
    national_code: str = VALID_NATIONAL_CODE,
    status: UserStatus = UserStatus.ACTIVE,
):
    user = User(
        bale_user_id=bale_user_id,
        phone_number=f"0912{bale_user_id:07d}",
        national_code=national_code,
        first_name="Test",
        last_name="User",
        status=status,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def create_exam(
    db_session,
    exam_code: str = "TEST-001",
    title: str = "Ø¢Ø²Ù…ÙˆÙ† Ø¢Ø²Ù…Ø§ÛŒØ´ÛŒ",
):
    exam = Exam(
        title=title,
        exam_code=exam_code,
        exam_date=date.today(),
        total_score=20,
        passing_score=10,
    )

    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)

    return exam


@pytest.fixture
def sent_messages(monkeypatch):
    messages = []

    async def fake_send_message(chat_id, text):
        messages.append(
            {
                "chat_id": chat_id,
                "text": text,
            }
        )

    monkeypatch.setattr(
        "app.bot.handlers.query.bale_client.send_message",
        fake_send_message,
    )

    return messages


@pytest.mark.anyio
async def test_result_inquiry_rejects_invalid_national_code(
    db_session,
    sent_messages,
):
    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1001,
        chat_id=2001,
        national_code="123",
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == 2001
    assert sent_messages[0]["text"]


@pytest.mark.anyio
async def test_result_inquiry_rejects_unregistered_user(
    db_session,
    sent_messages,
):
    await handle_result_inquiry(
        db=db_session,
        bale_user_id=999999,
        chat_id=2002,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == 2002
    assert sent_messages[0]["text"]


@pytest.mark.anyio
async def test_result_inquiry_rejects_disabled_user(
    db_session,
    sent_messages,
):
    create_user(
        db_session,
        bale_user_id=1002,
        status=UserStatus.DISABLED,
    )

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1002,
        chat_id=2003,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == 2003
    assert sent_messages[0]["text"]


@pytest.mark.anyio
async def test_result_inquiry_rejects_national_code_mismatch(
    db_session,
    sent_messages,
):
    create_user(
        db_session,
        bale_user_id=1003,
        national_code=VALID_NATIONAL_CODE,
    )

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1003,
        chat_id=2004,
        national_code="1111111103",
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == 2004
    assert sent_messages[0]["text"]


@pytest.mark.anyio
async def test_result_inquiry_when_no_published_results(
    db_session,
    sent_messages,
):
    create_user(
        db_session,
        bale_user_id=1004,
    )

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1004,
        chat_id=2005,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == 2005
    assert sent_messages[0]["text"]


@pytest.mark.anyio
async def test_result_inquiry_returns_published_passed_result(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1005,
    )

    exam = create_exam(
        db_session,
        exam_code="TEST-001",
        title="Ø¢Ø²Ù…ÙˆÙ† Ø¢Ø²Ù…Ø§ÛŒØ´ÛŒ",
    )

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=18,
        is_passed=True,
        status=ResultStatus.PUBLISHED,
        published_at=datetime.now(timezone.utc),
    )

    db_session.add(result)
    db_session.commit()

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1005,
        chat_id=2006,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1

    message = sent_messages[0]

    assert message["chat_id"] == 2006
    assert "18" in message["text"]


@pytest.mark.anyio
async def test_result_inquiry_returns_published_failed_result(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1006,
    )

    exam = create_exam(
        db_session,
        exam_code="TEST-002",
        title="Ø¢Ø²Ù…ÙˆÙ† Ù…Ø±Ø¯ÙˆØ¯ÛŒ",
    )

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=7,
        is_passed=False,
        status=ResultStatus.PUBLISHED,
        published_at=datetime.now(timezone.utc),
    )

    db_session.add(result)
    db_session.commit()

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1006,
        chat_id=2007,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1

    message = sent_messages[0]

    assert message["chat_id"] == 2007
    assert "7" in message["text"]


@pytest.mark.anyio
async def test_result_inquiry_ignores_unpublished_results(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1007,
    )

    exam = create_exam(
        db_session,
        exam_code="TEST-003",
    )

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=19,
        is_passed=True,
        status=ResultStatus.REVIEWED,
        published_at=None,
    )

    db_session.add(result)
    db_session.commit()

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1007,
        chat_id=2008,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == 2008
    assert sent_messages[0]["text"]


@pytest.mark.anyio
async def test_result_inquiry_returns_multiple_published_results(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1008,
    )

    exam1 = create_exam(
        db_session,
        exam_code="TEST-004",
        title="Ø¢Ø²Ù…ÙˆÙ† Ø§ÙˆÙ„",
    )

    exam2 = create_exam(
        db_session,
        exam_code="TEST-005",
        title="Ø¢Ø²Ù…ÙˆÙ† Ø¯ÙˆÙ…",
    )

    result1 = Result(
        user_id=user.id,
        exam_id=exam1.id,
        score=15,
        is_passed=True,
        status=ResultStatus.PUBLISHED,
        published_at=datetime(
            2026,
            9,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    result2 = Result(
        user_id=user.id,
        exam_id=exam2.id,
        score=8,
        is_passed=False,
        status=ResultStatus.PUBLISHED,
        published_at=datetime(
            2026,
            9,
            2,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    db_session.add_all([result1, result2])
    db_session.commit()

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1008,
        chat_id=2009,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1

    message = sent_messages[0]

    assert message["chat_id"] == 2009
    assert "Ø¢Ø²Ù…ÙˆÙ† Ø§ÙˆÙ„" in message["text"]
    assert "Ø¢Ø²Ù…ÙˆÙ† Ø¯ÙˆÙ…" in message["text"]
    assert "15" in message["text"]
    assert "8" in message["text"]


@pytest.mark.anyio
async def test_result_inquiry_uses_custom_appearance_template(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1009,
    )

    exam = create_exam(
        db_session,
        exam_code="TEST-006",
        title="Ø¢Ø²Ù…ÙˆÙ† Ù‚Ø§Ù„Ø¨ Ø³ÙØ§Ø±Ø´ÛŒ",
    )

    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=17,
        is_passed=True,
        status=ResultStatus.PUBLISHED,
        published_at=datetime.now(timezone.utc),
    )

    db_session.add(result)
    db_session.commit()

    from app.models.appearance import AppearanceSettings

    appearance = AppearanceSettings(
        result_message_template=(
            "Ù†Ù…Ø±Ù‡ Ø´Ù…Ø§: {score} | ÙˆØ¶Ø¹ÛŒØª Ù†Ù‡Ø§ÛŒÛŒ: {status}"
        )
    )

    db_session.add(appearance)
    db_session.commit()
    db_session.commit()

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1009,
        chat_id=2010,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1

    message = sent_messages[0]

    assert "17" in message["text"]


@pytest.mark.anyio
async def test_result_inquiry_uses_custom_error_message_for_disabled_user(
    db_session,
    sent_messages,
):
    create_user(
        db_session,
        bale_user_id=1010,
        status=UserStatus.DISABLED,
    )

    from app.models.appearance import AppearanceSettings

    appearance = AppearanceSettings(
        error_message="Ù¾ÛŒØ§Ù… Ø®Ø·Ø§ÛŒ Ø³ÙØ§Ø±Ø´ÛŒ"
    )

    db_session.add(appearance)
    db_session.commit()

    await handle_result_inquiry(
        db=db_session,
        bale_user_id=1010,
        chat_id=2011,
        national_code=VALID_NATIONAL_CODE,
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["text"] == "Ù¾ÛŒØ§Ù… Ø®Ø·Ø§ÛŒ Ø³ÙØ§Ø±Ø´ÛŒ"
