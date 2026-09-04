import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.feature import FeatureFlag
from app.models.result import Result, ResultStatus
from app.models.user import User, UserStatus
from app.schemas.notification import BroadcastAudience
from app.services import notification_service


def make_feature(enabled=True):
    feature = MagicMock(spec=FeatureFlag)
    feature.key = "auto_notification"
    feature.is_enabled = enabled
    return feature


def make_user(
    user_id="user-1",
    bale_user_id=123456,
    status=UserStatus.ACTIVE,
):
    user = MagicMock(spec=User)
    user.id = user_id
    user.bale_user_id = bale_user_id
    user.status = status
    return user


def make_result(
    user_id="user-1",
    result_id="result-1",
    score=80,
    is_passed=True,
    notification_sent=False,
    exam_title="آزمون آزمایشی",
):
    result = MagicMock(spec=Result)
    result.id = result_id
    result.user_id = user_id
    result.score = score
    result.is_passed = is_passed
    result.notification_sent = notification_sent

    exam = MagicMock()
    exam.title = exam_title
    result.exam = exam

    return result


def test_is_feature_enabled_when_feature_enabled():
    db = MagicMock()
    feature = make_feature(enabled=True)

    db.query.return_value.filter.return_value.first.return_value = feature

    assert notification_service._is_feature_enabled(
        db,
        "auto_notification",
    ) is True


def test_is_feature_enabled_when_feature_disabled():
    db = MagicMock()
    feature = make_feature(enabled=False)

    db.query.return_value.filter.return_value.first.return_value = feature

    assert notification_service._is_feature_enabled(
        db,
        "auto_notification",
    ) is False


def test_is_feature_enabled_when_feature_does_not_exist():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    assert notification_service._is_feature_enabled(
        db,
        "auto_notification",
    ) is True


def test_notify_result_published_when_feature_disabled():
    db = MagicMock()
    result = make_result()

    with patch.object(
        notification_service,
        "_is_feature_enabled",
        return_value=False,
    ), patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        asyncio.run(
            notification_service.notify_result_published(
                db,
                result,
            )
        )

    mock_send.assert_not_awaited()
    db.commit.assert_not_called()


def test_notify_result_published_when_notification_already_sent():
    db = MagicMock()
    result = make_result(notification_sent=True)

    with patch.object(
        notification_service,
        "_is_feature_enabled",
        return_value=True,
    ), patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        asyncio.run(
            notification_service.notify_result_published(
                db,
                result,
            )
        )

    mock_send.assert_not_awaited()
    db.commit.assert_not_called()


def test_notify_result_published_when_user_does_not_exist():
    db = MagicMock()
    result = make_result()

    db.query.return_value.filter.return_value.first.return_value = None

    with patch.object(
        notification_service,
        "_is_feature_enabled",
        return_value=True,
    ), patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        asyncio.run(
            notification_service.notify_result_published(
                db,
                result,
            )
        )

    mock_send.assert_not_awaited()
    db.commit.assert_not_called()


def test_notify_result_published_when_user_is_disabled():
    db = MagicMock()
    result = make_result()

    user = make_user(status=UserStatus.DISABLED)

    db.query.return_value.filter.return_value.first.return_value = user

    with patch.object(
        notification_service,
        "_is_feature_enabled",
        return_value=True,
    ), patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        asyncio.run(
            notification_service.notify_result_published(
                db,
                result,
            )
        )

    mock_send.assert_not_awaited()
    db.commit.assert_not_called()


def test_notify_result_published_success_passed():
    db = MagicMock()
    result = make_result(
        score=95,
        is_passed=True,
    )
    user = make_user()

    db.query.return_value.filter.return_value.first.return_value = user

    with patch.object(
        notification_service,
        "_is_feature_enabled",
        return_value=True,
    ), patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        asyncio.run(
            notification_service.notify_result_published(
                db,
                result,
            )
        )

    mock_send.assert_awaited_once()

    args = mock_send.await_args.args

    assert args[0] == user.bale_user_id
    assert "95" in args[1]
    assert "قبول" in args[1]

    assert result.notification_sent is True
    db.commit.assert_called_once()


def test_notify_result_published_success_failed():
    db = MagicMock()
    result = make_result(
        score=35,
        is_passed=False,
    )
    user = make_user()

    db.query.return_value.filter.return_value.first.return_value = user

    with patch.object(
        notification_service,
        "_is_feature_enabled",
        return_value=True,
    ), patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        asyncio.run(
            notification_service.notify_result_published(
                db,
                result,
            )
        )

    mock_send.assert_awaited_once()

    args = mock_send.await_args.args

    assert args[0] == user.bale_user_id
    assert "35" in args[1]
    assert "مردود" in args[1]

    assert result.notification_sent is True
    db.commit.assert_called_once()


def test_notify_result_published_when_send_fails():
    db = MagicMock()
    result = make_result()
    user = make_user()

    db.query.return_value.filter.return_value.first.return_value = user

    with patch.object(
        notification_service,
        "_is_feature_enabled",
        return_value=True,
    ), patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.side_effect = RuntimeError("Bale API error")

        asyncio.run(
            notification_service.notify_result_published(
                db,
                result,
            )
        )

    mock_send.assert_awaited_once()
    assert result.notification_sent is False
    db.commit.assert_not_called()


def test_send_broadcast_all_success():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
        make_user("user-2", 102),
        make_user("user-3", 103),
    ]

    query = db.query.return_value
    filtered_query = query.filter.return_value
    filtered_query.all.return_value = users

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "سلام",
                BroadcastAudience.ALL,
            )
        )

    assert sent == 3
    assert failed == 0
    assert mock_send.await_count == 3


def test_send_broadcast_all_with_failure():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
        make_user("user-2", 102),
        make_user("user-3", 103),
    ]

    db.query.return_value.filter.return_value.all.return_value = users

    async def send_side_effect(user_id, message):
        if user_id == 102:
            raise RuntimeError("send failed")

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.side_effect = send_side_effect

        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "سلام",
                BroadcastAudience.ALL,
            )
        )

    assert sent == 2
    assert failed == 1
    assert mock_send.await_count == 3


def test_send_broadcast_exam_participants():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
        make_user("user-2", 102),
    ]

    main_query = db.query.return_value
    active_query = main_query.filter.return_value

    user_id_query = MagicMock()
    user_id_filtered = user_id_query.filter.return_value

    db.query.side_effect = [
        main_query,
        user_id_query,
    ]

    active_query.filter.return_value.all.return_value = users

    exam_id = "exam-123"

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "پیام آزمون",
                BroadcastAudience.EXAM_PARTICIPANTS,
                exam_id,
            )
        )

    assert sent == 2
    assert failed == 0
    assert mock_send.await_count == 2

    user_id_query.filter.assert_called_once()


def test_send_broadcast_passed():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
    ]

    main_query = MagicMock()
    active_query = MagicMock()
    user_id_query = MagicMock()
    user_id_filtered = MagicMock()

    db.query.side_effect = [
        main_query,
        user_id_query,
    ]

    main_query.filter.return_value = active_query
    active_query.filter.return_value.all.return_value = users

    user_id_query.filter.return_value = user_id_filtered

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "قبول شدگان",
                BroadcastAudience.PASSED,
                "exam-123",
            )
        )

    assert sent == 1
    assert failed == 0
    mock_send.assert_awaited_once()


def test_send_broadcast_failed():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
    ]

    main_query = MagicMock()
    active_query = MagicMock()
    user_id_query = MagicMock()
    user_id_filtered = MagicMock()

    db.query.side_effect = [
        main_query,
        user_id_query,
    ]

    main_query.filter.return_value = active_query
    active_query.filter.return_value.all.return_value = users

    user_id_query.filter.return_value = user_id_filtered

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "مردود شدگان",
                BroadcastAudience.FAILED,
                "exam-123",
            )
        )

    assert sent == 1
    assert failed == 0
    mock_send.assert_awaited_once()


def test_send_broadcast_exam_participants_without_exam_id():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
    ]

    db.query.return_value.filter.return_value.all.return_value = users

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "پیام",
                BroadcastAudience.EXAM_PARTICIPANTS,
                None,
            )
        )

    assert sent == 1
    assert failed == 0
    mock_send.assert_awaited_once()


def test_send_broadcast_passed_without_exam_id():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
    ]

    db.query.return_value.filter.return_value.all.return_value = users

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "پیام",
                BroadcastAudience.PASSED,
                None,
            )
        )

    assert sent == 1
    assert failed == 0
    mock_send.assert_awaited_once()


def test_send_broadcast_failed_without_exam_id():
    db = MagicMock()

    users = [
        make_user("user-1", 101),
    ]

    db.query.return_value.filter.return_value.all.return_value = users

    with patch.object(
        notification_service.bale_client,
        "send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        sent, failed = asyncio.run(
            notification_service.send_broadcast(
                db,
                "پیام",
                BroadcastAudience.FAILED,
                None,
            )
        )

    assert sent == 1
    assert failed == 0
    mock_send.assert_awaited_once()