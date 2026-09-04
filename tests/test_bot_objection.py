import pytest

from app.bot.handlers.objection import (
    _pending_objection,
    handle_objection_input,
    handle_objection_start,
    has_pending_objection,
)
from app.models.feature import FeatureFlag
from app.models.objection import Objection
from app.models.result import Result, ResultStatus
from app.models.user import User, UserStatus
from app.models.exam import Exam


VALID_NATIONAL_CODE = "1234567891"


def create_user(
    db_session,
    bale_user_id,
    national_code=VALID_NATIONAL_CODE,
):
    user = User(
        bale_user_id=bale_user_id,
        phone_number=f"0912{bale_user_id:07d}",
        national_code=national_code,
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_exam(
    db_session,
    exam_code="TEST-001",
    title="آزمون آزمایشی",
):
    exam = Exam(
        title=title,
        exam_code=exam_code,
        exam_date=__import__("datetime").date.today(),
        total_score=20,
        passing_score=10,
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


def create_published_result(
    db_session,
    user,
    exam,
    score=15,
):
    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=score,
        is_passed=score >= exam.passing_score,
        status=ResultStatus.PUBLISHED,
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    return result


@pytest.fixture()
def sent_messages(monkeypatch):
    messages = []

    async def fake_send_message(chat_id, text):
        messages.append((chat_id, text))

    monkeypatch.setattr(
        "app.bot.handlers.objection.bale_client.send_message",
        fake_send_message,
    )

    return messages


@pytest.fixture(autouse=True)
def clear_pending_objection():
    _pending_objection.clear()
    yield
    _pending_objection.clear()


def test_has_pending_objection_returns_false_when_no_state():
    assert has_pending_objection(9001) is False


def test_has_pending_objection_returns_true_when_state_exists():
    _pending_objection[9002] = {
        "step": "choosing_result",
        "results": [],
    }

    assert has_pending_objection(9002) is True


@pytest.mark.anyio
async def test_handle_objection_start_when_feature_disabled(
    db_session,
    sent_messages,
):
    feature = FeatureFlag(
        key="objection",
            display_name="?????? ?? ????",
        is_enabled=False,
    )
    db_session.add(feature)
    db_session.commit()

    await handle_objection_start(
        db_session,
        bale_user_id=1001,
        chat_id=2001,
    )

    assert len(sent_messages) == 1
    assert sent_messages[0][0] == 2001
    assert "غیرفعال" in sent_messages[0][1]
    assert 1001 not in _pending_objection


@pytest.mark.anyio
async def test_handle_objection_start_when_feature_missing_is_enabled_by_default(
    db_session,
    sent_messages,
):
    await handle_objection_start(
        db_session,
        bale_user_id=1002,
        chat_id=2002,
    )

    assert len(sent_messages) == 1
    assert "ابتدا" in sent_messages[0][1]
    assert 1002 not in _pending_objection


@pytest.mark.anyio
async def test_handle_objection_start_unregistered_user(
    db_session,
    sent_messages,
):
    feature = FeatureFlag(
        key="objection",
            display_name="?????? ?? ????",
        is_enabled=True,
    )
    db_session.add(feature)
    db_session.commit()

    await handle_objection_start(
        db_session,
        bale_user_id=1003,
        chat_id=2003,
    )

    assert len(sent_messages) == 1
    assert "ابتدا" in sent_messages[0][1]
    assert 1003 not in _pending_objection


@pytest.mark.anyio
async def test_handle_objection_start_without_published_results(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1004,
    )

    await handle_objection_start(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=2004,
    )

    assert len(sent_messages) == 1
    assert "نتیجه" in sent_messages[0][1]
    assert 1004 not in _pending_objection


@pytest.mark.anyio
async def test_handle_objection_start_creates_pending_state(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1005,
    )
    exam = create_exam(
        db_session,
        exam_code="TEST-005",
        title="آزمون پنجم",
    )
    result = create_published_result(
        db_session,
        user,
        exam,
        score=17,
    )

    await handle_objection_start(
        db_session,
        bale_user_id=1005,
        chat_id=2005,
    )

    assert len(sent_messages) == 1
    assert "آزمون پنجم" in sent_messages[0][1]
    assert "17" in sent_messages[0][1]

    assert has_pending_objection(1005) is True
    assert _pending_objection[1005]["step"] == "choosing_result"
    assert _pending_objection[1005]["results"] == [str(result.id)]


@pytest.mark.anyio
async def test_handle_objection_start_lists_multiple_results(
    db_session,
    sent_messages,
):
    user = create_user(
        db_session,
        bale_user_id=1006,
    )

    exam1 = create_exam(
        db_session,
        exam_code="TEST-006-A",
        title="آزمون اول",
    )
    exam2 = create_exam(
        db_session,
        exam_code="TEST-006-B",
        title="آزمون دوم",
    )

    result1 = create_published_result(
        db_session,
        user,
        exam1,
        score=12,
    )
    result2 = create_published_result(
        db_session,
        user,
        exam2,
        score=18,
    )

    await handle_objection_start(
        db_session,
        bale_user_id=1006,
        chat_id=2006,
    )

    assert len(sent_messages) == 1

    message = sent_messages[0][1]

    assert "آزمون اول" in message
    assert "آزمون دوم" in message
    assert "12" in message
    assert "18" in message

    assert _pending_objection[1006]["results"] == [
        str(result1.id),
        str(result2.id),
    ]


@pytest.mark.anyio
async def test_handle_objection_input_without_state_returns_false(
    db_session,
    sent_messages,
):
    result = await handle_objection_input(
        db_session,
        bale_user_id=1007,
        chat_id=2007,
        text="1",
    )

    assert result is False
    assert sent_messages == []


@pytest.mark.anyio
async def test_handle_objection_input_invalid_number_returns_true(
    db_session,
    sent_messages,
):
    _pending_objection[1008] = {
        "step": "choosing_result",
        "results": ["result-id"],
    }

    result = await handle_objection_input(
        db_session,
        bale_user_id=1008,
        chat_id=2008,
        text="abc",
    )

    assert result is True
    assert len(sent_messages) == 1
    assert "نامعتبر" in sent_messages[0][1]

    assert _pending_objection[1008]["step"] == "choosing_result"


@pytest.mark.anyio
async def test_handle_objection_input_out_of_range_number_returns_true(
    db_session,
    sent_messages,
):
    _pending_objection[1009] = {
        "step": "choosing_result",
        "results": ["result-id"],
    }

    result = await handle_objection_input(
        db_session,
        bale_user_id=1009,
        chat_id=2009,
        text="2",
    )

    assert result is True
    assert len(sent_messages) == 1
    assert "نامعتبر" in sent_messages[0][1]

    assert _pending_objection[1009]["step"] == "choosing_result"


@pytest.mark.anyio
async def test_handle_objection_input_valid_number_moves_to_description(
    db_session,
    sent_messages,
):
    _pending_objection[1010] = {
        "step": "choosing_result",
        "results": ["result-1", "result-2"],
    }

    result = await handle_objection_input(
        db_session,
        bale_user_id=1010,
        chat_id=2010,
        text=" 2 ",
    )

    assert result is True
    assert len(sent_messages) == 1
    assert "دلیل" in sent_messages[0][1]

    assert _pending_objection[1010]["step"] == "awaiting_description"
    assert _pending_objection[1010]["result_id"] == "result-2"


@pytest.mark.anyio
async def test_handle_objection_input_unknown_state_returns_false(
    db_session,
    sent_messages,
):
    _pending_objection[1011] = {
        "step": "unexpected_step",
    }

    result = await handle_objection_input(
        db_session,
        bale_user_id=1011,
        chat_id=2011,
        text="test",
    )

    assert result is False
    assert sent_messages == []
    assert has_pending_objection(1011) is True


@pytest.mark.anyio
async def test_handle_objection_input_saves_objection_and_audit_log(
    db_session,
    sent_messages,
):
    from app.models.audit import AuditLog

    user = create_user(
        db_session,
        bale_user_id=1012,
    )
    exam = create_exam(
        db_session,
        exam_code="TEST-012",
        title="آزمون اعتراض",
    )
    result = create_published_result(
        db_session,
        user,
        exam,
        score=8,
    )

    _pending_objection[1012] = {
        "step": "awaiting_description",
        "result_id": str(result.id),
    }

    response = await handle_objection_input(
        db_session,
        bale_user_id=1012,
        chat_id=2012,
        text="  به نمره سوال سوم اعتراض دارم  ",
    )

    assert response is True

    objection = (
        db_session.query(Objection)
        .filter(
            Objection.user_id == user.id,
            Objection.result_id == result.id,
        )
        .first()
    )

    assert objection is not None
    assert objection.description == "به نمره سوال سوم اعتراض دارم"

    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "objection_submitted",
        )
        .first()
    )

    assert audit is not None
    assert audit.actor_type == "user"
    assert audit.target_type == "objection"
    assert audit.target_id == str(objection.id)

    assert 1012 not in _pending_objection

    assert len(sent_messages) == 1
    assert "ثبت" in sent_messages[0][1]