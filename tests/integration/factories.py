from functools import partial
from typing import Any

import anyio
from fastapi.testclient import TestClient

from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos import CreateUserDTO
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.use_cases import CreateUserUseCase
from fastapi_template.entrypoints.fastapi.factories import FastAPIFactory
from tests.foundation.factories import ContainerBasedFactory


class UserPromotionError(Exception):
    pass


class TestClientFactory(ContainerBasedFactory):
    def __call__(
        self,
        auth_for_user: User | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> TestClient:
        api_factory = self._container.resolve(FastAPIFactory)
        jwt_service = self._container.resolve(JWTService)

        headers = headers or {}

        if auth_for_user is not None:
            token = jwt_service.issue_access_token(user_id=auth_for_user.id)
            headers["Authorization"] = f"Bearer {token}"

        app = api_factory(
            add_trusted_hosts_middleware=False,
            add_cors_middleware=False,
        )

        return TestClient(
            app=app,
            headers=headers,
            base_url="http://testserver",
            **kwargs,
        )


class TestUserFactory(ContainerBasedFactory):
    def __call__(
        self,
        username: str = "test_user",
        password: str | None = None,
        email: str | None = None,
        *,
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> User:
        create_user = partial(
            self._create_user,
            username=username,
            password=password or _valid_test_credential(),
            email=email,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        return anyio.run(create_user)

    async def _create_user(
        self,
        *,
        username: str,
        password: str,
        email: str | None,
        is_staff: bool,
        is_superuser: bool,
    ) -> User:
        create_user_use_case = self._container.resolve(CreateUserUseCase)
        user = await create_user_use_case.execute(
            data=CreateUserDTO(
                username=username,
                email=email or f"{username}@test.com",
                first_name="Test",
                last_name="User",
                password=password,
            ),
        )
        if not is_staff and not is_superuser:
            return user

        return await self._promote_user(
            user=user,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )

    async def _promote_user(
        self,
        *,
        user: User,
        is_staff: bool,
        is_superuser: bool,
    ) -> User:
        uow = self._container.resolve(UnitOfWork)
        async with uow as active_uow:
            promoted_user = await active_uow.user_repository.set_access_flags(
                user_id=user.id,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )

        if promoted_user is None:
            raise UserPromotionError

        return promoted_user


def _valid_test_credential() -> str:
    return "S3cure-test-password-123!"
