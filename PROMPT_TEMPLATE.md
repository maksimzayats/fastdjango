# modern-python-template Project Creation Prompt

Use this after creating an empty repository for your project and opening that
repository in an LLM coding agent.

Before pasting the prompt below into the agent, set the project name, update any
optional bracketed values, and remove any removable capability bullets you do
not want. The edited prompt is the setup input for your generated project, and
it points the agent at the modern-python-template GitHub repository to use as
the source template.

```text
You are an LLM coding agent working in an empty repository for my generated
project. Assume the current working directory is that repository.

Template source: https://github.com/maksimzayats/modern-python-template

Generated project identity:
- Project name: [Human-readable project name]

Naming defaults:
- Derive the Python distribution name from the project name by lowercasing it,
  replacing spaces and underscores with hyphens, and removing characters that
  are not valid in Python distribution names.
- Derive the Python package/import name from the project name by lowercasing it,
  replacing spaces and hyphens with underscores, removing characters that are
  not valid in Python identifiers, and making sure the result is a valid Python
  package name.
- Derive Docker, Compose, environment, docs, and display names from the project
  name using the conventional form for each target.
- If I add an explicit natural-language override for any derived name, use that
  override instead of the default derivation.

Template identifiers:
- Current template import root: modern_python_template
- Short description: [one-sentence product description]
- Repository URL: [https://github.com/org/repo or none]
- Local browser origins: [http://localhost:3000, http://localhost:8000, ...]

Goal:
Create the generated project in this repository by using the template source
above as the starting codebase. Treat my edited prompt as the setup source of
truth. Do not use a separate interactive setup flow. Keep every capability
explicitly listed below and delete every removable capability that is not listed.

Mandatory modern-python-template Base:
- Keep FastAPI delivery.
- Keep Django ORM, migrations, and admin.
- Keep dependency injection with diwire.
- Keep architecture guardrails.
- Keep tests, linting, formatting, and strict typing.

Removable capabilities to keep:
- Celery background tasks and beat scheduler.
- Authentication endpoints, JWT access tokens, and refresh sessions.
- Request throttling and rate limiting.
- Storage backends: local filesystem, local MinIO, and remote S3-compatible storage.
- Observability with Logfire/OpenTelemetry.
- MkDocs documentation site and docs publishing.
- Docker services: PostgreSQL, PgBouncer, Redis, and MinIO.
- GitHub workflows for CI and docs publishing.
- Example domains: health, user, and authentication.

Implementation rules:
- Start with `git status --short` and preserve existing user changes.
- Bring the modern-python-template code from the template source into this
  repository before customizing it. Preserve this repository's Git history and
  configured `origin`; do not replace them with the template repository's Git
  metadata.
- Rename the project metadata, package imports, Docker/Compose names, settings,
  docs, tests, and examples to match the generated project identity.
- Write development `.env` values from the kept capabilities. Keep committed
  environment examples current and do not commit secrets.
- For every removable capability omitted from this prompt, delete its code,
  tests, docs, dependencies, settings, environment variables, Docker services,
  Make targets, and workflows. Do not leave dormant configuration behind.
- Remove template-only setup artifacts from the generated project unless I ask
  to keep them: `PROMPT_TEMPLATE.md`, `CONTEXT.md`, and `docs/adr/`.
- Keep controller, use-case/service, transaction, exception-contract, model, and
  dependency-injection conventions intact.
- Run `uv lock` after dependency changes.
- Validate with the narrowest meaningful checks, preferring `make lint` and
  `make test` when practical.
- Finish by summarizing changed files, removed capabilities, and exact checks
  run.
```
