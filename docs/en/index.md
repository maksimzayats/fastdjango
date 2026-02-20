# Fast Django

A production-ready Django + FastAPI + Celery template with dependency injection, type safety, and modern Python practices.

## Why Fast Django?

This template provides a solid foundation for building scalable Python applications by combining:

- **Django** for ORM, admin panel, and authentication
- **FastAPI** for high-performance REST APIs
- **Celery** for background task processing
- **diwire** for dependency injection
- **Pydantic** for validation and settings management
- **Logfire** for observability (OpenTelemetry-based)

## Key Features

- **Service Layer Architecture**: Clean separation between HTTP controllers and database operations
- **Auto-Registration IoC**: Minimal boilerplate dependency injection with automatic wiring
- **Type Safety**: Full `mypy --strict` compatibility with Python 3.14+
- **Test Isolation**: Per-test container instances with easy mocking
- **Unified Controller Pattern**: Same pattern for HTTP endpoints and Celery tasks

## Quick Links

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
Controller → Service → Model

✅ Controller imports Service
✅ Service imports Model
❌ Controller imports Model (NEVER)
```

Controllers handle HTTP/Celery concerns. Services contain business logic and database operations. Models define data structures.

## Requirements

- Python 3.14+
- Docker and Docker Compose
- uv (Python package manager)

## Getting Help

- [GitHub Issues](https://github.com/MaksimZayats/fastdjango/issues) - Report bugs or request features
- [Project Structure](getting-started/project-structure.md) - Understand the codebase organization
