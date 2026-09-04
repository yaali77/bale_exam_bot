
import uuid
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql, sqlite

from app.core.db_types import GUID


def test_guid_load_dialect_impl_postgresql():
    guid = GUID()
    dialect = postgresql.dialect()

    result = guid.load_dialect_impl(dialect)

    assert isinstance(result, postgresql.UUID)
    assert result.as_uuid is True


def test_guid_load_dialect_impl_non_postgresql():
    guid = GUID()
    dialect = sqlite.dialect()

    result = guid.load_dialect_impl(dialect)

    assert result.length == 32


def test_guid_process_bind_param_none():
    guid = GUID()
    dialect = sqlite.dialect()

    assert guid.process_bind_param(None, dialect) is None


def test_guid_process_bind_param_postgresql_uuid():
    guid = GUID()
    dialect = postgresql.dialect()
    value = uuid.uuid4()

    result = guid.process_bind_param(value, dialect)

    assert result == str(value)


def test_guid_process_bind_param_postgresql_string():
    guid = GUID()
    dialect = postgresql.dialect()
    value = str(uuid.uuid4())

    result = guid.process_bind_param(value, dialect)

    assert result == value


def test_guid_process_bind_param_sqlite_uuid():
    guid = GUID()
    dialect = sqlite.dialect()
    value = uuid.uuid4()

    result = guid.process_bind_param(value, dialect)

    assert result == value.hex


def test_guid_process_bind_param_sqlite_string():
    guid = GUID()
    dialect = sqlite.dialect()
    value = str(uuid.uuid4())

    result = guid.process_bind_param(value, dialect)

    assert result == uuid.UUID(value).hex


def test_guid_process_result_value_none():
    guid = GUID()
    dialect = sqlite.dialect()

    assert guid.process_result_value(None, dialect) is None


def test_guid_process_result_value_uuid():
    guid = GUID()
    dialect = sqlite.dialect()
    value = uuid.uuid4()

    result = guid.process_result_value(value, dialect)

    assert result is value


def test_guid_process_result_value_string():
    guid = GUID()
    dialect = sqlite.dialect()
    value = uuid.uuid4()

    result = guid.process_result_value(str(value), dialect)

    assert result == value
