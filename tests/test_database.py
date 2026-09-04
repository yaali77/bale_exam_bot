from unittest.mock import MagicMock

import app.database as database


def test_get_db_yields_session_and_closes(monkeypatch):
    mock_db = MagicMock()

    monkeypatch.setattr(
        database,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database.get_db()

    db = next(generator)

    assert db is mock_db

    generator.close()

    mock_db.close.assert_called_once()


def test_get_db_closes_session_when_exception_occurs(monkeypatch):
    mock_db = MagicMock()

    monkeypatch.setattr(
        database,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database.get_db()

    db = next(generator)

    assert db is mock_db

    try:
        generator.throw(RuntimeError("test error"))
    except RuntimeError as exc:
        assert str(exc) == "test error"

    mock_db.close.assert_called_once()
