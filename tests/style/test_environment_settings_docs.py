from pathlib import Path

from tests.architecture._source import REPO_ROOT

ENVIRONMENT_REFERENCE = REPO_ROOT / "docs" / "en" / "reference" / "environment-variables.md"
EXAMPLE_FILES = (
    REPO_ROOT / ".env.example",
    REPO_ROOT / ".env.test.example",
)
DOCUMENTED_ENVIRONMENT_VARIABLES = {
    "ALLOWED_HOSTS",
    "CORS_ALLOW_CREDENTIALS",
    "CORS_ALLOW_HEADERS",
    "CORS_ALLOW_METHODS",
    "CORS_ALLOW_ORIGINS",
    "DATABASE_ECHO",
    "DATABASE_URL",
    "ENVIRONMENT",
    "INSTRUMENTOR_FASTAPI_EXCLUDED_URLS",
    "IP_HEADER",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "JWT_ALGORITHM",
    "JWT_SECRET_KEY",
    "JWT_TYP",
    "LOGFIRE_ENABLED",
    "LOGFIRE_ENVIRONMENT",
    "LOGFIRE_SERVICE_NAME",
    "LOGFIRE_SERVICE_VERSION",
    "LOGFIRE_TOKEN",
    "LOGGING_LEVEL",
    "PASSWORD_MAX_LENGTH",
    "PASSWORD_MIN_LENGTH",
    "REDIS_URL",
    "REFRESH_SESSION_REFRESH_TOKEN_NBYTES",
    "REFRESH_SESSION_REFRESH_TOKEN_TTL_DAYS",
    "TIME_ZONE",
    "TRUST_FORWARDED_IP_HEADER",
    "USER_AGENT_HEADER",
    "VERSION",
}
EXAMPLE_ENVIRONMENT_VARIABLES = {
    "DATABASE_URL",
    "ENVIRONMENT",
    "IP_HEADER",
    "JWT_SECRET_KEY",
    "LOGFIRE_ENABLED",
    "LOGGING_LEVEL",
    "REDIS_URL",
    "REFRESH_SESSION_REFRESH_TOKEN_NBYTES",
    "REFRESH_SESSION_REFRESH_TOKEN_TTL_DAYS",
    "TRUST_FORWARDED_IP_HEADER",
}


def test_environment_reference_documents_all_runtime_settings() -> None:
    reference_text = ENVIRONMENT_REFERENCE.read_text(encoding="utf-8")
    missing_names = sorted(
        name for name in DOCUMENTED_ENVIRONMENT_VARIABLES if f"`{name}`" not in reference_text
    )

    assert missing_names == []


def test_environment_examples_cover_required_settings() -> None:
    example_text = "\n".join(
        path.read_text(encoding="utf-8") for path in EXAMPLE_FILES if Path(path).exists()
    )
    missing_names = sorted(
        name for name in EXAMPLE_ENVIRONMENT_VARIABLES if f"{name}=" not in example_text
    )

    assert missing_names == []
