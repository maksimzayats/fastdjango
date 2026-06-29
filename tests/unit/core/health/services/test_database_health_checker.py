from typing import cast

import pytest

from fastapi_template.core.health.services.database_health_checker import DatabaseHealthChecker


def test_database_health_checker_requires_concrete_implementation() -> None:
    checker_type = cast(type[object], DatabaseHealthChecker)

    with pytest.raises(TypeError, match="abstract"):
        checker_type()
