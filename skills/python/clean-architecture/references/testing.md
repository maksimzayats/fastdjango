# Testing Reference

Use this file when adding or refactoring tests, fixtures, DI overrides,
architecture guardrails, or style checks.

## Contents

- [Test Layout](#test-layout)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [Architecture Tests](#architecture-tests)
- [Fixture Boundaries](#fixture-boundaries)
- [Style Tests](#style-tests)
- [Verification](#verification)

## Test Layout

Prefer tests outside the import package:

```text
tests/
  unit/
  integration/
  architecture/
  style/
```

Create only the folders that the repo needs now.

Use `unit/` for isolated use cases and services. Use `integration/` for
framework entrypoints, database, messaging, HTTP clients, task runners, and
container wiring. Use `architecture/` for dependency-direction guardrails. Use
`style/` only for conventions that a linter cannot express clearly.

## Unit Tests

Unit tests should exercise application behavior without framework request
objects, routers, task decorators, or real external IO.

Prefer real deterministic collaborators. Replace only external IO, time,
randomness, network clients, framework resources, and slow persistence.

```python
from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class FakeUserStore(UserStore):
    created_email: str | None = None

    def create_user(self, *, email: str, password_hash: str) -> int:
        self.created_email = email
        return 123


def test_register_user_creates_user_with_hashed_password() -> None:
    user_store = FakeUserStore()
    use_case = RegisterUserUseCase(
        _password_hasher=PasswordHasher(),
        _user_store=user_store,
    )

    user_id = use_case.execute(
        command=RegisterUserCommand(email="ada@example.com", password="secret"),
    )

    assert user_id == 123
    assert user_store.created_email == "ada@example.com"
```

When the repo standardizes on container-based tests, override dependencies
before resolving the graph. Keep direct constructor tests for simple services
when that is clearer.

## Integration Tests

Integration tests may cross runtime boundaries intentionally. Keep them focused
on real seams:

- entrypoint to use case;
- container registration to resolved graph;
- persistence adapter to database;
- external client adapter to stubbed service;
- framework request/response serialization at the delivery edge.

Do not repeat every unit scenario through every delivery adapter. Test a few
representative paths and error translations.

## Architecture Tests

Add architecture tests when they protect a boundary that is easy to regress.
Keep them boring and explicit.

```python
import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src" / "example"


def _import_info(path: Path) -> tuple[set[str], set[str], dict[str, set[str]]]:
    tree = ast.parse(path.read_text())
    direct_imports: set[str] = set()
    imported_modules: set[str] = set()
    from_imports: dict[str, set[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            direct_imports.update(alias.name for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
            from_imports.setdefault(node.module, set()).update(
                alias.name for alias in node.names
            )

    return direct_imports, imported_modules, from_imports


def test_core_does_not_import_delivery_or_container() -> None:
    for path in (SRC_ROOT / "core").rglob("*.py"):
        direct_imports, imported_modules, from_imports = _import_info(path)

        assert not any(".delivery." in name for name in imported_modules), path
        assert not any(
            name == "diwire" or name.startswith("diwire.")
            for name in direct_imports
        ), path
        assert not any(name.startswith("diwire.") for name in from_imports), path
        assert not (
            from_imports.get("diwire", set()) & {"Container", "resolver_context"}
        ), path
```

Replace `example` with the repo's package name. Prefer a tiny helper over a
large custom architecture framework unless the repo already has one. This
example intentionally allows `from diwire import Injected` in `core`, but keeps
containers and resolver-context injection out of use cases and services.

## Fixture Boundaries

- Put shared fixtures in the nearest useful `conftest.py`.
- Keep domain object builders close to tests unless reused broadly.
- Avoid fixtures that hide the behavior under test.
- Prefer explicit setup in a test when it makes the test easier to read.
- Reset or rebuild containers per test when overrides are involved.

## Style Tests

Use style tests only for project-specific rules that `ruff`, formatters, or type
checkers do not cover.

Good candidates:

- injected dataclass field ordering;
- no `None` placeholder annotations for fields that need explicit optionality;
- no imports from delivery code inside core use cases/services;
- framework schemas do not appear in use-case method signatures.

Avoid style tests for subjective preferences unless the repo already enforces
them consistently.

## Verification

Use the repo's existing commands first. Typical checks are:

```bash
uv run pytest
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/architecture
```

Report exactly which checks ran and any checks that could not run.
