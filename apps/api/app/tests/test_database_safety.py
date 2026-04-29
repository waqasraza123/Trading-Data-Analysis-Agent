import pytest

from app.core.database_safety import (
    UnsafeDatabaseTargetError,
    environment_is_production_like,
    validate_smoke_database_target,
    validate_test_database_target,
)


def test_environment_is_production_like_checks_app_env_and_env() -> None:
    assert environment_is_production_like("production", None) is True
    assert environment_is_production_like(None, "prod") is True
    assert environment_is_production_like("test", "development") is False


def test_integration_safety_rejects_matching_test_and_database_url_in_production() -> None:
    database_url = "postgresql://user:password@host.neon.tech/prod"

    with pytest.raises(UnsafeDatabaseTargetError, match="TEST_DATABASE_URL equals DATABASE_URL"):
        validate_test_database_target(
            test_database_url=database_url,
            database_url=database_url,
            app_env="production",
            env=None,
            operation_name="DB integration tests",
        )


def test_integration_safety_allows_missing_database_url() -> None:
    validate_test_database_target(
        test_database_url="postgresql://user:password@localhost:5432/test",
        database_url=None,
        app_env="production",
        env=None,
        operation_name="DB integration tests",
    )


def test_smoke_safety_rejects_unsafe_test_database_target() -> None:
    database_url = "postgresql://user:password@host.neon.tech/prod"

    with pytest.raises(UnsafeDatabaseTargetError, match="Refusing smoke checks"):
        validate_smoke_database_target(
            database_url_env="TEST_DATABASE_URL",
            target_database_url=database_url,
            database_url=database_url,
            app_env="production",
            env=None,
            include_write_tests=False,
        )


def test_smoke_safety_rejects_write_checks_in_production_like_env() -> None:
    with pytest.raises(UnsafeDatabaseTargetError, match="Refusing smoke write tests"):
        validate_smoke_database_target(
            database_url_env="TEST_DATABASE_URL",
            target_database_url="postgresql://user:password@localhost:5432/test",
            database_url=None,
            app_env="production",
            env=None,
            include_write_tests=True,
        )
