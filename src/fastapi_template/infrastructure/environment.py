from enum import StrEnum


class Environment(StrEnum):
    """Define Environment."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"
    CI = "ci"
