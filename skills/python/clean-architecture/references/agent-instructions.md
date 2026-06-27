# Agent Instructions Reference

Use this file when creating or updating target-repo `AGENTS.md`, `CLAUDE.md`, or
similar coding-agent instruction files.

## Purpose

Agent instruction files should tell future coding agents how to work in this
repo without rereading every convention from scratch. Keep them concise,
command-focused, and specific to the repo.

Do not turn them into general clean-architecture essays. Link or point to local
docs only when those docs already exist and are useful.

## AGENTS.md

Create or update root `AGENTS.md` when the repo should give coding agents
stable project instructions.

Good content:

- project package name and `src/<package_name>` layout;
- install and check commands;
- architecture boundary rules;
- test layout and which checks to run for common changes;
- framework-specific entrypoint notes;
- files or directories agents should avoid touching without explicit request.

Template:

```markdown
# Agent Instructions

## Project Shape

- Python package lives under `src/example`.
- Application behavior belongs in `src/example/core`.
- External clients, persistence adapters, and framework integration belong at
  the edge or in `src/example/infrastructure`.
- Composition belongs in `src/example/ioc` and outer entrypoints.

## Commands

- Install: `uv sync`
- Test: `uv run pytest`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type check: `uv run mypy .`

## Architecture

- Use cases/services do not import delivery adapters, framework request/response
  objects, or `diwire.Container`.
- Inject collaborators with `Injected[...]`.
- Prefer concrete classes. Use ABCs only for real boundaries.

## Testing

- Put fast behavior tests in `tests/unit`.
- Put framework/database/container wiring tests in `tests/integration`.
- Put dependency-direction guardrails in `tests/architecture` when needed.
```

Replace `example` with the repo's package name and commands with the repo's real
commands.

## CLAUDE.md

Create or update `CLAUDE.md` only when the repo expects Claude Code users or
already has the file. Keep it aligned with `AGENTS.md`; avoid maintaining two
different sources of truth.

If both files exist, keep shared guidance short and identical where practical.
Put tool-specific instructions only where they belong.

Good `CLAUDE.md` additions:

- the same package layout and commands as `AGENTS.md`;
- Claude-specific workflow notes if the team uses them;
- pointers to existing local docs if Claude users rely on them.

Avoid:

- long architecture tutorials;
- stale command lists;
- model-specific prompting advice unrelated to this repo;
- duplicating every reference file from this skill.

## Update Rules

When changing agent docs:

1. Read existing `AGENTS.md`, `CLAUDE.md`, and local docs first.
2. Preserve useful local conventions.
3. Update commands to match the actual repo config.
4. Keep root instructions broad; use nested instruction files only when a
   subdirectory has genuinely different rules.
5. Run a markdown or repository validation command if one exists.
