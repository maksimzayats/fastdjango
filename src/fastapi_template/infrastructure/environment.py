from enum import StrEnum


class Environment(StrEnum):
    """Environment names used by settings and application bootstrap."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"
    CI = "ci"
