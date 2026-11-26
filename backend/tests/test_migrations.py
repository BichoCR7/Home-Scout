"""Alembic upgrade and downgrade smoke tests against an isolated SQLite file."""

from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from tests.test_database import FOUNDATION_TABLES


def make_alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = database_url
    return config


def test_migration_upgrade_and_downgrade(tmp_path) -> None:
    database_path = (tmp_path / "migration-test.db").as_posix()
    database_url = f"sqlite:///{database_path}"
    config = make_alembic_config(database_url)

    command.upgrade(config, "b5d5b46e253a")
    engine = create_engine(database_url)
    try:
        user_id = uuid4()
        role_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO user_accounts "
                    "(id, email, phone_number, status, created_at, updated_at) "
                    "VALUES (:id, :email, NULL, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": user_id.hex, "email": "legacy@example.com"},
            )
            connection.execute(
                text(
                    "INSERT INTO roles (id, code, name, description, created_at) "
                    "VALUES (:id, 'tenant', 'Tenant', 'Existing role', CURRENT_TIMESTAMP)"
                ),
                {"id": role_id.hex},
            )
            connection.execute(
                text(
                    "INSERT INTO user_role_assignments "
                    "(user_id, role_id, assigned_by_user_id, assigned_at) "
                    "VALUES (:user_id, :role_id, NULL, CURRENT_TIMESTAMP)"
                ),
                {"user_id": user_id.hex, "role_id": role_id.hex},
            )

        command.upgrade(config, "head")
        upgraded_tables = set(inspect(engine).get_table_names())
        assert FOUNDATION_TABLES <= upgraded_tables
        assert "alembic_version" in upgraded_tables
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM roles")) == 9
            assert connection.scalar(text("SELECT COUNT(*) FROM role_permissions")) > 100
            columns = inspect(connection).get_pk_constraint("user_role_assignments")[
                "constrained_columns"
            ]
            assert columns == ["user_id", "role_id", "scope_type", "scope_id"]
            assignment = connection.execute(
                text(
                    "SELECT scope_type, scope_id FROM user_role_assignments "
                    "WHERE user_id = :user_id AND role_id = :role_id"
                ),
                {"user_id": user_id.hex, "role_id": role_id.hex},
            ).one()
            assert assignment == ("global", "*")
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(database_url)
    try:
        remaining_tables = set(inspect(engine).get_table_names())
        assert not FOUNDATION_TABLES.intersection(remaining_tables)
        assert "alembic_version" in remaining_tables
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) is None
    finally:
        engine.dispose()
