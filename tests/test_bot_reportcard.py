from unittest.mock import AsyncMock

import pytest

from app.bot import handlers
from app.bot.handlers import reportcard as reportcard_handler
from app.models.report_card import ReportCard
from app.models.user import User, UserStatus


def create_user(
    db_session,
    bale_user_id=987650300,
    phone_number="09121110030",
    national_code="1234567830",
    first_name="Ali",
    last_name="Karami",
    status=None,
):
    user = User(
        bale_user_id=bale_user_id,
        phone_number=phone_number,
        national_code=national_code,
        first_name=first_name,
        last_name=last_name,
    )

    if status is not None:
        user.status = status

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.mark.asyncio
async def test_report_card_handler_rejects_unknown_user(
    db_session,
    monkeypatch,
):
    send_message = AsyncMock()

    monkeypatch.setattr(
        reportcard_handler.bale_client,
        "send_message",
        send_message,
    )

    await reportcard_handler.handle_report_card_request(
        db_session,
        bale_user_id=999999999,
        chat_id=12345,
    )

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 12345
    assert "ثبت" in args[1]
    assert "/start" in args[1]


@pytest.mark.asyncio
async def test_report_card_handler_rejects_disabled_user(
    db_session,
    monkeypatch,
):
    user = create_user(
        db_session,
        status=UserStatus.DISABLED,
    )

    send_message = AsyncMock()

    monkeypatch.setattr(
        reportcard_handler.bale_client,
        "send_message",
        send_message,
    )

    await reportcard_handler.handle_report_card_request(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=12345,
    )

    send_message.assert_awaited_once()

    args = send_message.await_args.args

    assert args[0] == 12345
    assert "غیرفعال" in args[1]


@pytest.mark.asyncio
async def test_report_card_handler_reports_missing_pdf(
    db_session,
    monkeypatch,
):
    user = create_user(db_session)

    send_message = AsyncMock()
    send_document = AsyncMock()

    monkeypatch.setattr(
        reportcard_handler.bale_client,
        "send_message",
        send_message,
    )
    monkeypatch.setattr(
        reportcard_handler.bale_client,
        "send_document",
        send_document,
    )

    fake_report_card = ReportCard(
        user_id=user.id,
        report_number="RC-BOT-NOPDF",
        verification_code="VERIFY-BOT-NOPDF",
        pdf_path=None,
        qr_path=None,
        is_valid=True,
    )

    generate_report_card = lambda db, current_user: fake_report_card

    monkeypatch.setattr(
        "app.api.routers.reportcard.generate_or_refresh_report_card",
        generate_report_card,
    )

    await reportcard_handler.handle_report_card_request(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=12345,
    )

    assert send_message.await_count == 2
    send_document.assert_not_awaited()

    messages = [
        call.args[1]
        for call in send_message.await_args_list
    ]

    assert any("آماده" in message for message in messages)
    assert any("موجود نیست" in message for message in messages)


@pytest.mark.asyncio
async def test_report_card_handler_sends_pdf(
    db_session,
    monkeypatch,
):
    user = create_user(db_session)

    send_message = AsyncMock()
    send_document = AsyncMock()

    monkeypatch.setattr(
        reportcard_handler.bale_client,
        "send_message",
        send_message,
    )
    monkeypatch.setattr(
        reportcard_handler.bale_client,
        "send_document",
        send_document,
    )

    fake_report_card = ReportCard(
        user_id=user.id,
        report_number="RC-BOT-001",
        verification_code="VERIFY-BOT-001",
        pdf_path="reports/bot_report.pdf",
        qr_path="reports/bot_qr.png",
        is_valid=True,
    )

    monkeypatch.setattr(
        "app.api.routers.reportcard.generate_or_refresh_report_card",
        lambda db, current_user: fake_report_card,
    )

    await reportcard_handler.handle_report_card_request(
        db_session,
        bale_user_id=user.bale_user_id,
        chat_id=12345,
    )

    assert send_message.await_count == 1
    send_document.assert_awaited_once()

    args = send_document.await_args.args

    assert args[0] == 12345
    assert args[1] == "reports/bot_report.pdf"

    caption = send_document.await_args.kwargs["caption"]

    assert "RC-BOT-001" in caption
    assert "کارنامه" in caption
