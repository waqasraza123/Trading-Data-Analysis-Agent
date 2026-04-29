PRODUCTION_ENV_VALUES = {"prod", "production"}


class UnsafeDatabaseTargetError(RuntimeError):
    pass


def environment_is_production_like(app_env: str | None, env: str | None) -> bool:
    normalized_app_env = (app_env or "").strip().lower()
    normalized_env = (env or "").strip().lower()
    return normalized_app_env in PRODUCTION_ENV_VALUES or normalized_env in PRODUCTION_ENV_VALUES


def database_urls_match(first_url: str | None, second_url: str | None) -> bool:
    if first_url is None or second_url is None:
        return False
    return first_url.strip() == second_url.strip()


def validate_test_database_target(
    test_database_url: str | None,
    database_url: str | None,
    app_env: str | None,
    env: str | None,
    operation_name: str,
) -> None:
    if not database_urls_match(test_database_url, database_url):
        return
    if not environment_is_production_like(app_env, env):
        return
    msg = (
        f"Refusing {operation_name} because TEST_DATABASE_URL equals DATABASE_URL "
        "while APP_ENV or ENV is production-like"
    )
    raise UnsafeDatabaseTargetError(msg)


def validate_smoke_database_target(
    database_url_env: str,
    target_database_url: str,
    database_url: str | None,
    app_env: str | None,
    env: str | None,
    include_write_tests: bool,
) -> None:
    if database_url_env == "TEST_DATABASE_URL":
        validate_test_database_target(
            test_database_url=target_database_url,
            database_url=database_url,
            app_env=app_env,
            env=env,
            operation_name="smoke checks",
        )
    if include_write_tests and environment_is_production_like(app_env, env):
        msg = "Refusing smoke write tests while APP_ENV or ENV is production-like"
        raise UnsafeDatabaseTargetError(msg)
