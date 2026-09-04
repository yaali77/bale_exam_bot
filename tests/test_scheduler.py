import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.broadcast_job import BroadcastJobStatus
from app.services import scheduler as scheduler_module


def make_job(
    job_id="job-1",
    status=BroadcastJobStatus.SCHEDULED,
    scheduled_at=None,
):
    job = MagicMock()
    job.id = job_id
    job.message = "Test message"
    job.audience = "all"
    job.exam_id = None
    job.status = status
    job.scheduled_at = scheduled_at
    job.sent_count = 0
    job.failed_count = 0
    job.executed_at = None
    return job


def make_db(job):
    db = MagicMock()

    query = db.query.return_value
    filtered = query.filter.return_value
    filtered.first.return_value = job

    return db


def test_execute_broadcast_job_when_job_does_not_exist():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    with (
        patch.object(scheduler_module, "SessionLocal", return_value=db),
        patch.object(
            scheduler_module,
            "send_broadcast",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        asyncio.run(scheduler_module._execute_broadcast_job("missing-job"))

    mock_send.assert_not_awaited()
    db.commit.assert_not_called()
    db.close.assert_called_once()


def test_execute_broadcast_job_when_job_is_not_scheduled():
    job = make_job(status=BroadcastJobStatus.SENT)
    db = make_db(job)

    with (
        patch.object(scheduler_module, "SessionLocal", return_value=db),
        patch.object(
            scheduler_module,
            "send_broadcast",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        asyncio.run(scheduler_module._execute_broadcast_job("job-1"))

    mock_send.assert_not_awaited()
    db.commit.assert_not_called()
    db.close.assert_called_once()


def test_execute_broadcast_job_success():
    job = make_job()
    db = make_db(job)

    with (
        patch.object(scheduler_module, "SessionLocal", return_value=db),
        patch.object(
            scheduler_module,
            "send_broadcast",
            new_callable=AsyncMock,
        ) as mock_send,
        patch.object(
            scheduler_module,
            "datetime",
        ) as mock_datetime,
    ):
        mock_send.return_value = (8, 2)

        executed_at = datetime(
            2026,
            9,
            4,
            10,
            0,
            tzinfo=timezone.utc,
        )
        mock_datetime.now.return_value = executed_at

        asyncio.run(scheduler_module._execute_broadcast_job("job-1"))

    mock_send.assert_awaited_once_with(
        db,
        job.message,
        job.audience,
        job.exam_id,
    )

    assert job.sent_count == 8
    assert job.failed_count == 2
    assert job.status == BroadcastJobStatus.SENT
    assert job.executed_at == executed_at

    db.commit.assert_called_once()
    db.close.assert_called_once()


def test_execute_broadcast_job_exception_with_existing_job():
    job = make_job()
    db = make_db(job)

    with (
        patch.object(scheduler_module, "SessionLocal", return_value=db),
        patch.object(
            scheduler_module,
            "send_broadcast",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        mock_send.side_effect = RuntimeError("send failed")

        asyncio.run(scheduler_module._execute_broadcast_job("job-1"))

    assert job.status == BroadcastJobStatus.FAILED
    db.commit.assert_called_once()
    db.close.assert_called_once()


def test_execute_broadcast_job_exception_when_job_cannot_be_found_after_failure():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.side_effect = [
        make_job(),
        None,
    ]

    with (
        patch.object(scheduler_module, "SessionLocal", return_value=db),
        patch.object(
            scheduler_module,
            "send_broadcast",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        mock_send.side_effect = RuntimeError("send failed")

        asyncio.run(scheduler_module._execute_broadcast_job("job-1"))

    mock_send.assert_awaited_once()
    db.commit.assert_not_called()
    db.close.assert_called_once()


def test_schedule_broadcast_job():
    run_at = datetime(
        2026,
        9,
        5,
        12,
        0,
        tzinfo=timezone.utc,
    )

    with patch.object(scheduler_module.scheduler, "add_job") as mock_add_job:
        scheduler_module.schedule_broadcast_job("job-123", run_at)

    mock_add_job.assert_called_once_with(
        scheduler_module._execute_broadcast_job,
        trigger="date",
        run_date=run_at,
        args=["job-123"],
        id="broadcast_job-123",
        replace_existing=True,
        misfire_grace_time=3600,
    )


def test_cancel_broadcast_job_success():
    with patch.object(scheduler_module.scheduler, "remove_job") as mock_remove:
        scheduler_module.cancel_broadcast_job("job-123")

    mock_remove.assert_called_once_with("broadcast_job-123")


def test_cancel_broadcast_job_when_job_does_not_exist():
    with patch.object(scheduler_module.scheduler, "remove_job") as mock_remove:
        mock_remove.side_effect = Exception("job not found")

        scheduler_module.cancel_broadcast_job("job-123")

    mock_remove.assert_called_once_with("broadcast_job-123")


def test_run_backup_job_success():
    with (
        patch.object(
            scheduler_module,
            "run_database_backup",
        ) as mock_backup,
        patch.object(
            scheduler_module.asyncio,
            "to_thread",
            new_callable=AsyncMock,
        ) as mock_to_thread,
    ):
        asyncio.run(scheduler_module._run_backup_job())

    mock_to_thread.assert_awaited_once_with(mock_backup)


def test_run_backup_job_exception():
    with patch.object(
        scheduler_module.asyncio,
        "to_thread",
        new_callable=AsyncMock,
    ) as mock_to_thread:
        mock_to_thread.side_effect = RuntimeError("backup failed")

        asyncio.run(scheduler_module._run_backup_job())

    mock_to_thread.assert_awaited_once_with(
        scheduler_module.run_database_backup
    )


def test_init_scheduler_backup_enabled():
    with (
        patch.object(
            scheduler_module.settings,
            "BACKUP_ENABLED",
            True,
        ),
        patch.object(
            scheduler_module.settings,
            "BACKUP_CRON_HOUR",
            3,
        ),
        patch.object(
            scheduler_module,
            "SessionLocal",
        ) as mock_session_local,
        patch.object(
            scheduler_module.scheduler,
            "add_job",
        ) as mock_add_job,
        patch.object(
            scheduler_module.scheduler,
            "start",
        ) as mock_start,
    ):
        db = MagicMock()
        mock_session_local.return_value = db

        db.query.return_value.filter.return_value.all.return_value = []

        scheduler_module.init_scheduler()

    assert mock_add_job.call_count == 1

    args, kwargs = mock_add_job.call_args

    assert args[0] is scheduler_module._run_backup_job
    assert kwargs["id"] == "daily_backup"
    assert kwargs["replace_existing"] is True

    mock_start.assert_called_once()
    db.close.assert_called_once()


def test_init_scheduler_backup_disabled():
    with (
        patch.object(
            scheduler_module.settings,
            "BACKUP_ENABLED",
            False,
        ),
        patch.object(
            scheduler_module,
            "SessionLocal",
        ) as mock_session_local,
        patch.object(
            scheduler_module.scheduler,
            "add_job",
        ) as mock_add_job,
        patch.object(
            scheduler_module.scheduler,
            "start",
        ) as mock_start,
    ):
        db = MagicMock()
        mock_session_local.return_value = db

        db.query.return_value.filter.return_value.all.return_value = []

        scheduler_module.init_scheduler()

    mock_add_job.assert_not_called()
    mock_start.assert_called_once()
    db.close.assert_called_once()


def test_init_scheduler_schedules_future_job():
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)

    job = make_job(
        job_id="future-job",
        status=BroadcastJobStatus.SCHEDULED,
        scheduled_at=future_time,
    )

    with (
        patch.object(
            scheduler_module.settings,
            "BACKUP_ENABLED",
            False,
        ),
        patch.object(
            scheduler_module,
            "SessionLocal",
        ) as mock_session_local,
        patch.object(
            scheduler_module,
            "schedule_broadcast_job",
        ) as mock_schedule,
        patch.object(
            scheduler_module.scheduler,
            "start",
        ),
    ):
        db = MagicMock()
        mock_session_local.return_value = db
        db.query.return_value.filter.return_value.all.return_value = [job]

        scheduler_module.init_scheduler()

    mock_schedule.assert_called_once_with(
        "future-job",
        future_time,
    )
    db.close.assert_called_once()


def test_init_scheduler_schedules_past_job_immediately():
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)

    job = make_job(
        job_id="past-job",
        status=BroadcastJobStatus.SCHEDULED,
        scheduled_at=past_time,
    )

    with (
        patch.object(
            scheduler_module.settings,
            "BACKUP_ENABLED",
            False,
        ),
        patch.object(
            scheduler_module,
            "SessionLocal",
        ) as mock_session_local,
        patch.object(
            scheduler_module,
            "schedule_broadcast_job",
        ) as mock_schedule,
        patch.object(
            scheduler_module.scheduler,
            "start",
        ),
    ):
        db = MagicMock()
        mock_session_local.return_value = db
        db.query.return_value.filter.return_value.all.return_value = [job]

        scheduler_module.init_scheduler()

    mock_schedule.assert_called_once()

    scheduled_job_id, scheduled_time = mock_schedule.call_args.args

    assert scheduled_job_id == "past-job"

    assert abs(
        (scheduled_time - datetime.now(timezone.utc)).total_seconds()
    ) < 5

    db.close.assert_called_once()


def test_init_scheduler_ignores_job_without_scheduled_at():
    job = make_job(
        job_id="no-date-job",
        status=BroadcastJobStatus.SCHEDULED,
        scheduled_at=None,
    )

    with (
        patch.object(
            scheduler_module.settings,
            "BACKUP_ENABLED",
            False,
        ),
        patch.object(
            scheduler_module,
            "SessionLocal",
        ) as mock_session_local,
        patch.object(
            scheduler_module,
            "schedule_broadcast_job",
        ) as mock_schedule,
        patch.object(
            scheduler_module.scheduler,
            "start",
        ),
    ):
        db = MagicMock()
        mock_session_local.return_value = db
        db.query.return_value.filter.return_value.all.return_value = [job]

        scheduler_module.init_scheduler()

    mock_schedule.assert_not_called()
    db.close.assert_called_once()


def test_shutdown_scheduler_when_running():
    with (
        patch.object(
            scheduler_module.scheduler,
            "running",
            True,
        ),
        patch.object(
            scheduler_module.scheduler,
            "shutdown",
        ) as mock_shutdown,
    ):
        scheduler_module.shutdown_scheduler()

    mock_shutdown.assert_called_once_with(wait=False)

def test_shutdown_scheduler_when_running():
    mock_scheduler = MagicMock()
    mock_scheduler.running = True

    with patch.object(
        scheduler_module,
        "scheduler",
        mock_scheduler,
    ):
        scheduler_module.shutdown_scheduler()

    mock_scheduler.shutdown.assert_called_once_with(wait=False)


def test_shutdown_scheduler_when_not_running():
    mock_scheduler = MagicMock()
    mock_scheduler.running = False

    with patch.object(
        scheduler_module,
        "scheduler",
        mock_scheduler,
    ):
        scheduler_module.shutdown_scheduler()

    mock_scheduler.shutdown.assert_not_called()