# Concepts

Understand the architectural patterns and design decisions behind the template.

## In This Section

| Concept | What You'll Learn |
|---------|-------------------|
| [Service Layer](service-layer.md) | Why controllers use use cases or services instead of querying models directly |
| [IoC Container](ioc-container.md) | How dependency injection works |
| [Controller Pattern](controller-pattern.md) | Unified handling for HTTP and Celery |
| [Factory Pattern](factory-pattern.md) | Complex object construction |
| [Pydantic Settings](pydantic-settings.md) | Configuration management |

## The Big Picture

The architecture follows a layered approach with clear boundaries:

```
┌─────────────────────────────────────────────────────────────┐
│                     Delivery Layer                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │        HTTP API         │  │      Celery Tasks       │  │
│  │      Controllers        │  │      Controllers        │  │
│  └───────────┬─────────────┘  └───────────┬─────────────┘  │
└──────────────┼────────────────────────────┼─────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Composition, Foundation, Infrastructure        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Entrypoints │ IoC (diwire) │ Base classes │ Settings │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              DTOs, Services, Use Cases               │   │
│  │   UserUseCase  │  TodoService  │  JWTService        │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                     Models                           │   │
│  │      User      │     Todo      │ Auth RefreshSession│   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Principles

### 1. The Golden Rule

```
Controller → Use Case / Service → Model

✅ Controller calls a use case or service
✅ Use cases and services own ORM access
❌ Controller queries models directly
```

This boundary ensures testability and maintainability.

### 2. Dependency Injection

All components receive their dependencies via constructor injection. The IoC container handles wiring automatically.

### 3. Type Safety

Everything is strictly typed. The codebase passes `mypy --strict`.

### 4. Convention over Configuration

Services and use cases are auto-registered when resolved. DTOs live beside use cases. Delivery schemas have their own base and may inherit from DTOs only when that keeps the API shape simple. Settings load from environment variables automatically. Minimal boilerplate is required.

## When to Read These

- **New to the project?** Start with [Service Layer](service-layer.md) and [IoC Container](ioc-container.md)
- **Building features?** Review [Controller Pattern](controller-pattern.md)
- **Need configuration?** Check [Pydantic Settings](pydantic-settings.md)
- **Complex construction?** Learn about [Factory Pattern](factory-pattern.md)
