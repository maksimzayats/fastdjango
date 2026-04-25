---
name: docs-reader
description: Answers questions using project documentation in docs/en/.
version: 1.0.0
---

# Documentation Reader Skill

Use this skill to answer questions from the maintained documentation in `docs/en/`.
Prefer the docs over memory, and point users to the smallest relevant page.

## Documentation Map

| User Intent | Section | Location |
|-------------|---------|----------|
| Learn by building | Tutorial | `docs/en/tutorial/` |
| Complete a task | How-To Guides | `docs/en/how-to/` |
| Understand a pattern | Concepts | `docs/en/concepts/` |
| Look up facts | Reference | `docs/en/reference/` |

## Start Here

| Question | Read |
|----------|------|
| Setup | `docs/en/getting-started/quick-start.md` |
| Project layout | `docs/en/getting-started/project-structure.md` |
| Add a domain | `docs/en/how-to/add-new-domain.md` |
| Add a Celery task | `docs/en/how-to/add-celery-task.md` |
| Write tests | `docs/en/tutorial/06-testing.md` |
| Environment variables | `docs/en/reference/environment-variables.md` |
| Make commands | `docs/en/reference/makefile.md` |
| Docker services | `docs/en/reference/docker-services.md` |

## Architecture Summary

```
Controller -> Use Case / Service -> Model
```

- Controllers handle FastAPI or Celery delivery concerns.
- Use cases and services own application logic and ORM access.
- Models define database structure.
- Base contracts live in `src/fastdjango/foundation/`.
- Domain delivery lives inside `src/fastdjango/core/<domain>/delivery/`.
- App composition lives in `src/fastdjango/entrypoints/`.

## Current Technology Notes

- Dependency injection uses `diwire` with recursive auto-wiring.
- Most classes do not need explicit IoC registration.
- HTTP controllers use `BaseController` or Django-aware `BaseTransactionController`.
- Async HTTP controllers use `BaseAsyncController`.
- Celery result schemas inherit from `BaseCelerySchema`.
- FastAPI schemas inherit from `BaseFastAPISchema`.

For deeper lookup, see the reference files in this skill.
