from functools import partial
from typing import Any, cast

import anyio
from fastapi.testclient import TestClient

from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.authentication.services.refresh_session import RefreshSessionService
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos.persist_user import PersistUserDTO
from fastapi_template.core.user.dtos.register_user import RegisterUserDTO
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.services.password import PasswordService
from fastapi_template.core.user.use_cases.register_user import RegisterUserUseCase
from fastapi_template.entrypoints.fastapi.factory import FastAPIFactory
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
        is_active: bool = True,
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> User:
        create_user = partial(
            self._create_user,
            username=username,
            password=password or _valid_test_credential(),
            email=email,
            is_active=is_active,
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
        is_active: bool,
        is_staff: bool,
        is_superuser: bool,
    ) -> User:
        if not is_active:
            return await self._persist_user(
                username=username,
                password=password,
                email=email,
                is_active=is_active,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )

        register_user_use_case = self._container.resolve(RegisterUserUseCase)
        user = await register_user_use_case.execute(
            data=RegisterUserDTO(
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
        uow = cast(UnitOfWork, self._container.resolve(UnitOfWork))
        async with uow as active_uow:
            promoted_user = await active_uow.user_repository.set_access_flags(
                user_id=user.id,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )

        if promoted_user is None:
            raise UserPromotionError

        return promoted_user

    async def _persist_user(
        self,
        *,
        username: str,
        password: str,
        email: str | None,
        is_active: bool,
        is_staff: bool,
        is_superuser: bool,
    ) -> User:
        password_service = self._container.resolve(PasswordService)
        uow = cast(UnitOfWork, self._container.resolve(UnitOfWork))
        async with uow as active_uow:
            return await active_uow.user_repository.create(
                data=PersistUserDTO(
                    username=username,
                    email=email or f"{username}@test.com",
                    first_name="Test",
                    last_name="User",
                    is_active=is_active,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                ),
                password_hash=password_service.hash_password(password=password),
            )


class TestRefreshSessionFactory(ContainerBasedFactory):
    def __call__(
        self,
        *,
        user: User,
        user_agent: str = "test",
        ip_address_trace: str | None = None,
    ) -> str:
        create_refresh_session = partial(
            self._create_refresh_session,
            user=user,
            user_agent=user_agent,
            ip_address_trace=ip_address_trace,
        )
        return anyio.run(create_refresh_session)

    async def _create_refresh_session(
        self,
        *,
        user: User,
        user_agent: str,
        ip_address_trace: str | None,
    ) -> str:
        refresh_session_service = self._container.resolve(RefreshSessionService)
        uow = cast(UnitOfWork, self._container.resolve(UnitOfWork))
        async with uow as active_uow:
            result = await refresh_session_service.create_refresh_session(
                uow=active_uow,
                user=user,
                user_agent=user_agent,
                ip_address_trace=ip_address_trace,
            )

        return result.refresh_token


def _valid_test_credential() -> str:
    return "S3cure-test-password-123!"
