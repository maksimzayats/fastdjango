# API Routes Reference

Use this file when creating or refactoring HTTP API routes, controllers,
request/response schemas, route registration, or API versioning.

## Contents

- [Rule](#rule)
- [Route Boundary](#route-boundary)
- [Route Shape](#route-shape)
- [Controller Example](#controller-example)
- [Versioning](#versioning)
- [Error Mapping](#error-mapping)
- [Checks](#checks)

## Rule

Public HTTP API routes must be defined as full paths beginning with `/api/v1`.
Do not split paths across router/base prefixes and route-local fragments.

Every route constant and route registration should contain the complete public
path, for example `/api/v1/users/{user_id}`. Do not define a base path such as
`/api/v1` or `/users` and then combine it with `/{user_id}` elsewhere.
Use the chosen framework's route registration API, but pass the full public path
to it.

Avoid these patterns:

```text
base_path = "/api/v1"
users_path = "/users"
route = base_path + users_path

router(prefix="/api/v1")
router.add("/users/{user_id}")
```

Use this pattern:

```text
GET    /api/v1/users/{user_id}
POST   /api/v1/users
PATCH  /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}
```

## Route Boundary

Route handlers and controllers are delivery adapters. They may depend on use
cases, application services for very small workflows, delivery schemas, and
framework objects. They must not contain business workflows or persistence
queries.

Responsibilities:

- accept framework request data;
- validate and parse delivery schemas;
- map request schemas to command DTOs;
- call a use case or focused application service;
- map result DTOs to response schemas;
- translate application exceptions to HTTP responses.

Do not pass framework request/response objects or delivery schemas into use
cases/services.

## Route Shape

Use full resource-oriented paths beginning with `/api/v1` unless the product
language clearly needs an action route:

```text
GET    /api/v1/users/{user_id}
POST   /api/v1/users
PATCH  /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}
POST   /api/v1/sessions
DELETE /api/v1/sessions/{session_id}
```

Use action routes sparingly:

```text
POST /api/v1/orders/{order_id}/cancel
POST /api/v1/reports/{report_id}/publish
```

## Controller Example

Keep the controller framework-adapter shape thin. The exact router registration
depends on the framework the user chooses.

```python
from dataclasses import dataclass

from diwire import Injected


REGISTER_USER_ROUTE = "/api/v1/users"
USER_DETAIL_ROUTE = "/api/v1/users/{user_id}"


@dataclass(frozen=True, kw_only=True, slots=True)
class RegisterUserRequest:
    email: str
    password: str


@dataclass(frozen=True, kw_only=True, slots=True)
class RegisterUserResponse:
    user_id: int


@dataclass(kw_only=True, slots=True)
class UserApiController:
    _register_user: Injected[RegisterUserUseCase]

    def register_user(
        self,
        *,
        request: RegisterUserRequest,
    ) -> RegisterUserResponse:
        user_id = self._register_user.execute(
            command=RegisterUserCommand(
                email=request.email,
                password=request.password,
            ),
        )
        return RegisterUserResponse(user_id=user_id)
```

Framework-specific code should bind the full `POST /api/v1/users` path to
`UserApiController.register_user` at the delivery edge. Do not rely on a router
base path plus a local `"/users"` fragment.

## Versioning

- Keep `/api/v1` stable once exposed.
- Add `/api/v2` only when behavior or schemas need breaking changes.
- Reuse the same use cases behind multiple API versions when application
  behavior is the same.
- Keep version-specific request/response schemas in delivery code.
- Do not leak API versioning into core services unless the domain behavior is
  genuinely versioned.

## Error Mapping

Translate application exceptions in delivery code:

Continuation of the controller shape above:

```python
@dataclass(kw_only=True, slots=True)
class UserApiController:
    _register_user: Injected[RegisterUserUseCase]

    def register_user(
        self,
        *,
        request: RegisterUserRequest,
    ) -> RegisterUserResponse:
        try:
            user_id = self._register_user.execute(
                command=RegisterUserCommand(
                    email=request.email,
                    password=request.password,
                ),
            )
        except UserAlreadyExistsError as error:
            raise ConflictHttpError("User already exists") from error

        return RegisterUserResponse(user_id=user_id)
```

Replace `ConflictHttpError` with the framework's HTTP error type or the repo's
existing delivery error abstraction.

## Checks

Before finishing route work, check:

- every public route is defined as a full `/api/v1/...` path;
- no router/base path is used to assemble public API route paths;
- no route path is split across constants, router prefixes, decorators, or
  registration helpers;
- route/controller code does not contain business workflows;
- delivery schemas are mapped to command/result DTOs at the edge;
- use cases/services do not import routers, request schemas, response schemas,
  or framework HTTP objects;
- error translation stays in delivery code.
