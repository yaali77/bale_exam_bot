import os
import time
from unittest.mock import patch

from app.services import backup_service


def test_parse_db_url_with_port():
    with patch.object(
        backup_service.settings,
        "DATABASE_URL",
        "postgresql+psycopg2://test_user:test_pass@localhost:5433/test_db",
    ):
        result = backup_service._parse_db_url()

    assert result == {
        "host": "localhost",
        "port": "5433",
        "user": "test_user",
        "password": "test_pass",
        "dbname": "test_db",
    }


def test_parse_db_url_without_port():
    with patch.object(
        backup_service.settings,
        "DATABASE_URL",
        "postgresql+psycopg2://test_user:test_pass@localhost/test_db",
    ):
        result = backup_service._parse_db_url()

    assert result["host"] == "localhost"
    assert result["port"] == "5432"
    assert result["user"] == "test_user"
    assert result["password"] == "test_pass"
    assert result["dbname"] == "test_db"


def test_run_database_backup_skipped_for_non_postgresql():
    with patch.object(
        backup_service.settings,
        "DATABASE_URL",
        "sqlite:///./test.db",
    ):
        result = backup_service.run_database_backup()

    assert result is None


def test_run_database_backup_success_with_password(tmp_path):
    backup_dir = tmp_path / "backups"

    with (
        patch.object(backup_service, "BACKUP_DIR", str(backup_dir)),
        patch.object(
            backup_service.settings,
            "DATABASE_URL",
            "postgresql+psycopg2://test_user:test_pass@localhost:5432/test_db",
        ),
        patch.object(backup_service.settings, "BACKUP_RETENTION_DAYS", 7),
        patch.object(backup_service.subprocess, "run") as mock_run,
    ):
        mock_run.side_effect = [
            type("Proc", (), {"stdout": b"SQL BACKUP DATA"})(),
            type("Proc", (), {"stdout": b"COMPRESSED DATA"})(),
        ]

        result = backup_service.run_database_backup()

    assert result is not None
    assert result.startswith(str(backup_dir))
    assert result.endswith(".sql.gz")
    assert os.path.exists(result)

    assert mock_run.call_count == 2

    first_call = mock_run.call_args_list[0]
    second_call = mock_run.call_args_list[1]

    assert first_call.args[0][0] == "pg_dump"
    assert first_call.kwargs["check"] is True
    assert first_call.kwargs["stdout"] == backup_service.subprocess.PIPE
    assert first_call.kwargs["stderr"] == backup_service.subprocess.PIPE
    assert first_call.kwargs["env"]["PGPASSWORD"] == "test_pass"

    assert second_call.args[0] == ["gzip"]
    assert second_call.kwargs["input"] == b"SQL BACKUP DATA"
    assert second_call.kwargs["check"] is True


def test_run_database_backup_without_password(tmp_path):
    backup_dir = tmp_path / "backups"

    with (
        patch.object(backup_service, "BACKUP_DIR", str(backup_dir)),
        patch.object(
            backup_service.settings,
            "DATABASE_URL",
            "postgresql+psycopg2://test_user@localhost/test_db",
        ),
        patch.object(backup_service.settings, "BACKUP_RETENTION_DAYS", 7),
        patch.object(backup_service.subprocess, "run") as mock_run,
    ):
        mock_run.side_effect = [
            type("Proc", (), {"stdout": b"SQL DATA"})(),
            type("Proc", (), {"stdout": b"GZIP DATA"})(),
        ]

        result = backup_service.run_database_backup()

    assert result is not None
    assert os.path.exists(result)

    first_call = mock_run.call_args_list[0]
    env = first_call.kwargs["env"]

    assert "PGPASSWORD" not in env


def test_cleanup_old_backups_when_directory_does_not_exist(tmp_path):
    backup_dir = tmp_path / "does_not_exist"

    with patch.object(backup_service, "BACKUP_DIR", str(backup_dir)):
        backup_service._cleanup_old_backups()

    assert not backup_dir.exists()


def test_cleanup_old_backups_removes_old_files_and_keeps_new_files(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    old_file = backup_dir / "old.sql.gz"
    new_file = backup_dir / "new.sql.gz"
    directory = backup_dir / "some_directory"

    old_file.write_bytes(b"old")
    new_file.write_bytes(b"new")
    directory.mkdir()

    old_timestamp = time.time() - (10 * 86400)
    new_timestamp = time.time()

    os.utime(old_file, (old_timestamp, old_timestamp))
    os.utime(new_file, (new_timestamp, new_timestamp))

    with (
        patch.object(backup_service, "BACKUP_DIR", str(backup_dir)),
        patch.object(
            backup_service.settings,
            "BACKUP_RETENTION_DAYS",
            7,
        ),
    ):
        backup_service._cleanup_old_backups()

    assert not old_file.exists()
    assert new_file.exists()
    assert directory.exists()


def test_list_backups_when_directory_does_not_exist(tmp_path):
    backup_dir = tmp_path / "missing"

    with patch.object(backup_service, "BACKUP_DIR", str(backup_dir)):
        result = backup_service.list_backups()

    assert result == []


def test_list_backups_returns_sorted_files_and_skips_directories(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    older = backup_dir / "backup_20260101_010101.sql.gz"
    newer = backup_dir / "backup_20260102_010101.sql.gz"
    directory = backup_dir / "not_a_file"

    older.write_bytes(b"old backup")
    newer.write_bytes(b"new backup")
    directory.mkdir()

    older_time = time.time() - 100
    newer_time = time.time()

    os.utime(older, (older_time, older_time))
    os.utime(newer, (newer_time, newer_time))

    with patch.object(backup_service, "BACKUP_DIR", str(backup_dir)):
        result = backup_service.list_backups()

    assert len(result) == 2

    assert result[0]["filename"] == "backup_20260102_010101.sql.gz"
    assert result[0]["size_bytes"] == len(b"new backup")
    assert "created_at" in result[0]

    assert result[1]["filename"] == "backup_20260101_010101.sql.gz"
    assert result[1]["size_bytes"] == len(b"old backup")
    assert "created_at" in result[1]