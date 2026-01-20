# Tutorial: Build a Todo List

Learn the architecture by building a complete feature from scratch.

## What You'll Build

In this tutorial, you'll create a fully-featured Todo List with:

- Django model with user ownership
- Service layer for business logic
- REST API with JWT authentication
- Background task for cleanup
- Observability with Logfire
- Comprehensive tests

## Prerequisites

Before starting, ensure you have:

- Completed the [Quick Start](../getting-started/quick-start.md)
- The development server running
- Basic familiarity with Django and FastAPI

## Tutorial Steps

| Step | What You'll Learn |
|------|-------------------|
| [1. Model & Service](01-model-and-service.md) | Create the Todo model and service layer |
| [2. IoC Registration](02-ioc-registration.md) | Understand automatic dependency injection |
| [3. HTTP API](03-http-api.md) | Build REST endpoints with authentication |
| [4. Celery Tasks](04-celery-tasks.md) | Add background task processing |
| [5. Observability](05-observability.md) | Configure logging and tracing |
| [6. Testing](06-testing.md) | Write integration tests |

## The Golden Rule

Throughout this tutorial, we follow the core architectural principle:

```
Controller → Service → Model

✅ Controller imports Service
✅ Service imports Model
❌ Controller imports Model (NEVER)
```

This separation ensures:

- **Testability**: Services can be tested without HTTP concerns
- **Reusability**: The same service works for HTTP, Celery, and CLI
- **Maintainability**: Clear boundaries make code easier to understand

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        HTTP Request                         │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     TodoController                          │
│  • Validates request data (Pydantic schemas)                │
│  • Calls service methods                                    │
│  • Returns response schemas                                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      TodoService                            │
│  • Contains business logic                                  │
│  • Performs database operations                             │
│  • Raises domain exceptions                                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Todo Model                            │
│  • Defines database schema                                  │
│  • Django ORM model                                         │
└─────────────────────────────────────────────────────────────┘
```

## Time to Complete

Each step takes approximately 15-30 minutes. The complete tutorial covers:

- Domain modeling and migrations
- Service layer patterns
- HTTP controllers and authentication
- Background task processing
- Observability setup
- Testing patterns

## Let's Begin

Ready to start? Head to [Step 1: Model & Service](01-model-and-service.md).
