# Factory Pattern

Factories handle complex object construction, especially when objects need configuration or produce different variants.

## When to Use Factories

Use factories when:

- Object construction requires configuration
- The same class has multiple valid configurations
- Construction logic is complex
- You need to delay or control instantiation

## JWTAuthFactory Example

The most common factory in this project is `JWTAuthFactory`:

```python
# src/delivery/http/auth/jwt.py
from dataclasses import dataclass


@dataclass(kw_only=True)
class JWTAuthFactory:
    """Factory for creating JWT authentication dependencies."""

    _jwt_service: JWTService
    _user_service: UserService

    def __call__(
        self,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> JWTAuth | JWTAuthWithPermissions:
        """Create a JWT auth dependency.

        Args:
            require_staff: If True, user must have is_staff=True
            require_superuser: If True, user must have is_superuser=True

        Returns:
            JWTAuth or JWTAuthWithPermissions instance
        """
        auth = JWTAuth(
            jwt_service=self._jwt_service,
            user_service=self._user_service,
        )

        if require_staff or require_superuser:
            return JWTAuthWithPermissions(
                auth=auth,
                require_staff=require_staff,
                require_superuser=require_superuser,
            )

        return auth
```

### Usage in Controllers

```python
@dataclass(kw_only=True)
class UserController(TransactionController):
    _jwt_auth_factory: JWTAuthFactory
    _user_service: UserService

    def __post_init__(self) -> None:
        # Create different auth configurations
        self._jwt_auth = self._jwt_auth_factory()
        self._staff_jwt_auth = self._jwt_auth_factory(require_staff=True)
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        # Public endpoint (no auth)
        registry.add_api_route("/v1/users/", self.create_user, methods=["POST"])

        # Authenticated endpoint
        registry.add_api_route(
            "/v1/users/me",
            self.get_current_user,
            methods=["GET"],
            dependencies=[Depends(self._jwt_auth)],
        )

        # Staff-only endpoint
        registry.add_api_route(
            "/v1/users/{user_id}",
            self.get_user_by_id,
            methods=["GET"],
            dependencies=[Depends(self._staff_jwt_auth)],
        )
```

Auth dependencies are created in `__post_init__` and stored as instance attributes (no `field(init=False)` needed).

## FastAPIFactory Example

The `FastAPIFactory` creates the entire FastAPI application:

```python
# src/delivery/http/factories.py
@dataclass(kw_only=True)
class FastAPIFactory:
    _application_settings: ApplicationSettings
    _http_settings: HTTPSettings
    _cors_settings: CORSSettings

    _lifespan: Lifespan
    _telemetry_instrumentor: OpenTelemetryInstrumentor
    _django_wsgi_factory: DjangoWSGIFactory

    # Controllers are injected as fields
    _health_controller: HealthController
    _user_token_controller: UserTokenController
    _user_controller: UserController

    def __call__(
        self,
        *,
        include_django: bool = True,
        add_trusted_hosts_middleware: bool = True,
        add_cors_middleware: bool = True,
    ) -> FastAPI:
        docs_url = (
            "/docs" if self._application_settings.environment != Environment.PRODUCTION else None
        )

        app = FastAPI(
            title="API",
            lifespan=self._lifespan,
            docs_url=docs_url,
            redoc_url=None,
        )

        self._telemetry_instrumentor.instrument_fastapi(app=app)
        self._add_middlewares(app=app, ...)
        self._register_controllers(app=app)

        if include_django:
            django_wsgi = self._django_wsgi_factory()
            app.mount("/django", WSGIMiddleware(django_wsgi))

        return app

    def _register_controllers(self, app: FastAPI) -> None:
        health_router = APIRouter(tags=["health"])
        self._health_controller.register(health_router)
        app.include_router(health_router)

        # ... more controllers
```

## ContainerBasedFactory

Test factories extend `ContainerBasedFactory` to access the IoC container:

```python
# src/infrastructure/delivery/factories.py
from abc import ABC
from dataclasses import dataclass

from ioc.container import AutoRegisteringContainer


@dataclass
class ContainerBasedFactory(ABC):
    """Base factory with access to IoC container."""

    _container: AutoRegisteringContainer
```

### TestClientFactory

```python
# tests/integration/factories.py
@dataclass
class TestClientFactory(ContainerBasedFactory):
    """Factory for creating test HTTP clients."""

    def __call__(
        self,
        auth_for_user: User | None = None,
        headers: dict[str, str] | None = None,
    ) -> Generator[TestClient, None, None]:
        """Create a test client.

        Args:
            auth_for_user: User to authenticate as (auto-generates token)
            headers: Additional headers to include

        Yields:
            Configured TestClient
        """
        final_headers = headers or {}

        if auth_for_user:
            jwt_service = self._container.resolve(JWTService)
            token = jwt_service.issue_access_token(user_id=auth_for_user.id)
            final_headers["Authorization"] = f"Bearer {token}"

        app = self._create_test_app()

        with TestClient(app, headers=final_headers) as client:
            yield client
```

## Factory vs Direct Instantiation

### When to Use Direct Instantiation

Simple objects without configuration:

```python
# Simple service with no config variants
service = TodoService()
```

### When to Use Factory

Objects with configuration options:

```python
# Factory allows different configurations
auth = jwt_auth_factory()  # Basic auth
staff_auth = jwt_auth_factory(require_staff=True)  # Staff auth
```

## Factory Registration

Factories are auto-registered like other services. If resolved by string key, explicit registration is needed:

```python
# src/ioc/registries.py
class Registry:
    def register(self, container: Container) -> None:
        container.register(
            "FastAPIFactory",
            factory=lambda: container.resolve(FastAPIFactory),
            scope=Scope.singleton,
        )
```

## CeleryAppFactory Example

```python
# src/delivery/tasks/factories.py
@dataclass(kw_only=True)
class CeleryAppFactory:
    """Factory for creating Celery applications."""

    _redis_settings: RedisSettings
    _logfire_settings: LogfireSettings

    _instance: ClassVar[Celery | None] = None

    def __call__(self) -> Celery:
        """Create or return the Celery application.

        Uses singleton pattern - only one Celery app per process.
        """
        if CeleryAppFactory._instance is not None:
            return CeleryAppFactory._instance

        celery_app = Celery(
            "tasks",
            broker=self._redis_settings.url,
            backend=self._redis_settings.url,
        )

        celery_app.conf.beat_schedule = {
            "ping-every-minute": {
                "task": TaskName.PING,
                "schedule": 60.0,
            },
        }

        CeleryAppFactory._instance = celery_app
        return celery_app
```

Note the singleton pattern: Celery should only have one app per process.

## Benefits

### 1. Flexible Configuration

```python
# Same factory, different configurations
basic_auth = factory()
staff_auth = factory(require_staff=True)
superuser_auth = factory(require_superuser=True)
```

### 2. Encapsulated Complexity

```python
# Complex construction hidden behind simple interface
app = fast_api_factory()  # All setup handled internally
```

### 3. Testability

```python
# Factories can be mocked or configured for tests
def test_with_custom_factory():
    factory = JWTAuthFactory(_jwt_service=mock_jwt, _user_service=mock_user)
    auth = factory()
    # Test with controlled dependencies
```

### 4. Lazy Initialization

```python
# Create factory early, instantiate later
def __post_init__(self) -> None:
    # Only creates auth when needed
    self._jwt_auth = self._jwt_auth_factory()
```

## Summary

Factories:

- **Encapsulate** complex construction logic
- **Enable** configurable object creation
- **Support** multiple variants from single factory
- **Integrate** with IoC container for dependencies
- **Improve** testability through controlled construction
