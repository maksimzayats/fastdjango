from typing import Any, cast

import pytest
from throttled import Quota

from fastapi_template.infrastructure.throttled import (
    throttler_factory as throttler_factory_module,
)
from fastapi_template.infrastructure.throttled.store_factory import ThrottlerStoreFactory
from fastapi_template.infrastructure.throttled.throttler_factory import ThrottlerFactory


class FakeStore:
    pass


class FakeThrottled:
    def __init__(self, *, using: str, quota: object, store: object) -> None:
        self.using = using
        self.quota = quota
        self.store = store


class FakeStoreFactory:
    def __init__(self, *, store: FakeStore) -> None:
        self.store = store

    def __call__(self) -> FakeStore:
        return self.store


def test_throttler_factory_builds_token_bucket_throttler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(throttler_factory_module, "Throttled", FakeThrottled)
    store = FakeStore()

    result = ThrottlerFactory(
        _store_factory=cast(ThrottlerStoreFactory, FakeStoreFactory(store=store)),
    )(cast(Quota, object()))
    fake_result = cast(Any, result)

    assert fake_result.store is store
    assert fake_result.using == "token_bucket"
