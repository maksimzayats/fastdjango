# Tooling Reference

Use this file when creating or updating Python project tooling, linting,
formatting, type-checking, dependency commands, or local check workflows.

## Contents

- [Principles](#principles)
- [Common Commands](#common-commands)
- [pyproject Defaults](#pyproject-defaults)
- [Ruff](#ruff)
- [mypy](#mypy)
- [Local Check Entry Points](#local-check-entry-points)
- [CI Notes](#ci-notes)

## Principles

- Preserve the repo's existing toolchain when it already works.
- Default to Python 3.14 for new repos unless the user asks for another version.
- Prefer `uv` for dependency and command execution when starting from scratch.
- Add dependencies with `uv add` or `uv add --dev` so `pyproject.toml` records
  the dependency requirement and version constraint. Do not hand-edit dependency
  lists unless preserving an existing repo convention requires it.
- Prefer `ruff` for linting and formatting unless the repo has a strong existing
  formatter/linter convention.
- Use `mypy` when type checking is expected; adopt strictness gradually in
  existing repos.
- Keep checks easy to run locally and in CI.
- Do not add tooling that is unrelated to the user's requested change.

## Common Commands

Use existing commands first. For a new repo, these are good defaults:

```bash
uv add diwire pydantic-settings
uv add --dev pytest ruff mypy
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

When fixing formatting:

```bash
uv run ruff format .
uv run ruff check . --fix
```

Run `ruff check --fix` only when the changes are expected and scoped.

## pyproject Defaults

For new repos, keep config small and explicit:

```toml
[project]
requires-python = ">=3.14"
dependencies = [
  "diwire",
  "pydantic-settings",
]

[dependency-groups]
dev = [
  "mypy",
  "pytest",
  "ruff",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 88
target-version = "py314"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
  "E",
  "F",
  "I",
  "UP",
  "B",
  "SIM",
]

[tool.mypy]
python_version = "3.14"
mypy_path = "src"
packages = ["example"]
```

Replace `example` with the repo's package name. Preserve an existing repo's
configured Python version unless the user asks to change it. Tighten `mypy` per
package once the current code is clean enough for stricter checks.

## Ruff

Use Ruff for import sorting, formatting, and common correctness checks. Avoid a
large rule set on the first pass unless the repo already uses one.

Good starting rule groups:

- `E`, `F`: basic pycodestyle and Pyflakes checks;
- `I`: import ordering;
- `UP`: pyupgrade rules;
- `B`: bugbear-style bug risks;
- `SIM`: simplification rules.

If a rule creates churn without protecting the architecture or behavior, leave
it out.

## mypy

Use type checking to protect service boundaries and DTO contracts. For existing
repos, prefer scoped strictness over one large failing switch:

```toml
[tool.mypy]
python_version = "3.14"
mypy_path = "src"
packages = ["example"]
warn_unused_ignores = true
warn_redundant_casts = true

[[tool.mypy.overrides]]
module = "example.core.*"
disallow_untyped_defs = true
```

Do not hide real type problems with broad `ignore_errors = true`. If third-party
libraries lack types, isolate ignores to those imports.

## Local Check Entry Points

If the repo uses a `Makefile`, `justfile`, task runner, or pre-commit-style
tool, keep one obvious command for the full local check:

```bash
uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy .
```

Use the repo's existing hook manager if present. Do not introduce a hook manager
only because one example uses it.

## CI Notes

CI should run the same commands as local development. Keep expensive integration
services separate from fast unit/lint/type checks when that makes feedback
faster.
