# Fast Django

A FastAPI + Django + Celery project template with a setup wizard, dependency
injection, typed settings, and practical architecture guardrails.

## Why Fast Django?

Fast Django gives you a backend template that can be cloned and customized
quickly without losing a clear application structure:

- **Django** for ORM, admin panel, and authentication
- **FastAPI** for high-performance REST APIs
- **Celery** for background task processing
- **diwire** for dependency injection
- **Pydantic** for validation and settings management
- **Logfire** for observability (OpenTelemetry-based)

## Start with setup

Recommended: create your own repository from this template on GitHub, clone it,
then run the wizard inside that checkout:

```bash
make setup
```

The wizard detects your repository from `origin`, preserves Git history, and
only asks whether to commit the generated setup changes.

If you clone the original template directly instead, use:

```bash
git clone https://github.com/maksimzayats/fastdjango.git && cd fastdjango && make setup
```

The wizard renames the checkout folder to the project slug, renames the project
and Python package, writes `.env`, configures database, Redis, storage, docs,
public origins, Logfire defaults, and Git setup for the flow you chose, then
prints the next commands.

## Key features

- **Use Case / Service Layer Architecture**: Clean separation between delivery and database operations
- **Auto-Registration IoC**: Minimal boilerplate dependency injection with automatic wiring
- **Type Safety**: Full `mypy --strict` compatibility with Python 3.14+
- **Test Isolation**: Per-test container instances with easy mocking
- **Unified Controller Pattern**: Same pattern for HTTP endpoints, Django delivery, and Celery tasks

## Quick links

<div class="grid cards" markdown>

-   :material-rocket-launch: **Getting Started**

    ---

    Get up and running in minutes

    [:octicons-arrow-right-24: Quick Start](getting-started/quick-start.md)

-   :material-school: **Tutorial**

    ---

    Learn by building a complete feature

    [:octicons-arrow-right-24: Build a Todo List](tutorial/index.md)

-   :material-lightbulb: **Concepts**

    ---

    Understand the architecture

    [:octicons-arrow-right-24: Core Concepts](concepts/index.md)

-   :material-clipboard-list: **How-To Guides**

    ---

    Solve specific problems

    [:octicons-arrow-right-24: How-To Guides](how-to/index.md)

</div>

## The Golden Rule

This template enforces a strict architectural boundary:

```
Controller → Use Case / Service → Model

✅ Controller calls a use case or service
✅ Use cases and services own ORM access
❌ Controller queries models directly
```

Controllers handle FastAPI, Django, and Celery delivery concerns. Use cases and
services contain application logic and database operations. Models define data
structures.

## Requirements

- Python 3.14+
- uv (Python package manager)
- Docker and Docker Compose for local infrastructure choices

## Getting Help

- [GitHub Issues](https://github.com/maksimzayats/fastdjango/issues) - Report bugs or request features
- [Project Structure](getting-started/project-structure.md) - Understand the codebase organization
