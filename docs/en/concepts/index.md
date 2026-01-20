# Concepts

Understand the architectural patterns and design decisions behind the template.

## In This Section

| Concept | What You'll Learn |
|---------|-------------------|
| [Service Layer](service-layer.md) | Why controllers don't access models directly |
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
│                    Infrastructure                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              IoC Container (punq)                    │   │
│  │   Auto-registration │ Settings │ Factories           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Services                          │   │
│  │   UserService  │  TodoService  │  JWTService        │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                     Models                           │   │
│  │      User      │     Todo      │  RefreshSession    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Principles

### 1. The Golden Rule

```
Controller → Service → Model

✅ Controller imports Service
✅ Service imports Model
❌ Controller imports Model (NEVER)
```

This boundary ensures testability and maintainability.

### 2. Dependency Injection

All components receive their dependencies via constructor injection. The IoC container handles wiring automatically.

### 3. Type Safety

Everything is strictly typed. The codebase passes `mypy --strict`.

### 4. Convention over Configuration

Services are auto-registered when resolved. Settings load from environment variables automatically. Minimal boilerplate is required.

## When to Read These

- **New to the project?** Start with [Service Layer](service-layer.md) and [IoC Container](ioc-container.md)
- **Building features?** Review [Controller Pattern](controller-pattern.md)
- **Need configuration?** Check [Pydantic Settings](pydantic-settings.md)
- **Complex construction?** Learn about [Factory Pattern](factory-pattern.md)
