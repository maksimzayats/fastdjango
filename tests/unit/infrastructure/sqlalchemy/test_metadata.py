from fastapi_template.infrastructure.sqlalchemy.metadata import target_metadata


def test_database_metadata_contains_application_tables() -> None:
    """Check database metadata imports all application tables."""
    assert {"users", "refresh_sessions"} <= set(target_metadata.tables)
