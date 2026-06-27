# Style Reference

Use this file when writing or refactoring Python classes, DTOs, method
signatures, imports, naming, or small snippets.

## Contents

- [Class Shape](#class-shape)
- [Naming](#naming)
- [Method Shape](#method-shape)
- [Control Flow](#control-flow)
- [Type Aliases](#type-aliases)
- [Imports](#imports)
- [`__init__.py` Files](#__init__py-files)
- [Errors](#errors)
- [Comments](#comments)

## Class Shape

Injectable classes should usually be keyword-only, slotted dataclasses:

```python
from dataclasses import dataclass

from diwire import Injected


@dataclass(frozen=True, kw_only=True, slots=True)
class IssueTokenCommand:
    user_id: int
    scopes: tuple[str, ...]


@dataclass(frozen=True, kw_only=True, slots=True)
class IssueTokenResult:
    access_token: str
    expires_in_seconds: int


@dataclass(kw_only=True, slots=True)
class Clock:
    def now(self) -> int:
        return 0


@dataclass(kw_only=True, slots=True)
class TokenIssuer:
    _clock: Injected[Clock]

    def issue_token(self, *, user_id: int, scopes: tuple[str, ...]) -> str:
        issued_at = self._clock.now()
        return f"{user_id}:{issued_at}:{','.join(scopes)}"


@dataclass(kw_only=True, slots=True)
class IssueTokenUseCase:
    _token_issuer: Injected[TokenIssuer]

    def execute(self, *, command: IssueTokenCommand) -> IssueTokenResult:
        access_token = self._token_issuer.issue_token(
            user_id=command.user_id,
            scopes=command.scopes,
        )
        return IssueTokenResult(
            access_token=access_token,
            expires_in_seconds=3600,
        )
```

Rules:

- Inject dependencies as private fields typed with `Injected[DependencyType]`.
- Prefer concrete dependency types by default.
- Prefer `@dataclass(kw_only=True, slots=True)` for services, use cases,
  adapters, controllers, and other regular classes.
- Keep non-DI constructor fields separate from injected fields with a blank line.
- Make public application method arguments keyword-only after `self`.
- Use `@dataclass(frozen=True, kw_only=True, slots=True)` for immutable
  command/result DTOs.
- Add tiny marker bases such as `BaseService` or `BaseUseCase` only when the repo
  already uses them or architecture tests will enforce them.

## Naming

Use names that describe owned behavior:

- `RegisterUserUseCase`
- `RefreshSessionUseCase`
- `PasswordHasher`
- `TokenIssuer`
- `OrderPricingService`
- `InventoryReservationService`

Avoid vague names:

- `UserManager`
- `AuthHelper`
- `CommonUtils`
- `DataHandler`

Do not split a class because there are many nouns. Split it when behavior,
dependencies, or lifecycle differ.

## Method Shape

Use `execute` for use cases when the repo has no stronger convention. Use
behavior-specific verbs for services.

```python
from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class PasswordHasher:
    def hash_password(self, *, raw_password: str) -> str:
        return f"hashed:{raw_password}"
```

Keep application method arguments keyword-only. This makes call sites clearer
and makes DTO migration easier.

## Control Flow

Keep branching shallow. Prefer early returns, early raises, guard clauses, and
small extracted methods over deeply nested `if`/`else`, `try`, or loop blocks.
Make the happy path easy to scan after invalid, missing, or exceptional cases
have exited.

Avoid hiding multiple application decisions inside one nested method. If a block
needs several levels of indentation, first look for a clearer boundary: a guard
clause, a focused service method, or a small private helper.

## Type Aliases

Define type aliases with `: TypeAlias`.

```python
from typing import TypeAlias


UserId: TypeAlias = int
Scopes: TypeAlias = tuple[str, ...]
```

Do not define type aliases with plain assignment:

```python
UserId = int
Scopes = tuple[str, ...]
```

Use type aliases sparingly. Prefer a dataclass or value object when the type
needs validation, behavior, or named fields.

Use this explicit `TypeAlias` form for this skill's style unless the user or the
existing repo explicitly standardizes on another alias syntax.

## Imports

Keep imports directional:

- delivery imports core;
- infrastructure imports core contracts when implementing adapters;
- `ioc` imports across layers to wire objects;
- core does not import delivery, entrypoint objects, container objects, or
  framework request/response classes.

Do not hide an import cycle by moving imports into functions unless that is a
temporary migration step with a clear follow-up.

## `__init__.py` Files

Keep `__init__.py` files empty by default.

Do not add any content to `__init__.py` files unless the user explicitly asks
for it. This includes:

- comments;
- docstrings;
- imports;
- re-exports;
- `__all__`;
- version constants;
- package metadata;
- convenience aliases.

Use direct imports from the module that owns the object instead of package-level
exports:

```python
from example.core.users.register_user import RegisterUserUseCase
```

Do not replace that with:

```python
from example.core.users import RegisterUserUseCase
```

## Errors

Prefer focused exception names close to the behavior:

```python
class UserAlreadyExistsError(Exception):
    pass
```

Delivery adapters translate application exceptions into framework responses.
Use cases and services should not raise framework exceptions directly.

## Comments

Add comments sparingly. Good comments explain non-obvious boundaries, tradeoffs,
or external system constraints. Avoid comments that restate the code.
