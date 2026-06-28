# Add an HTTP Endpoint

1. Add or choose a use case in `core/<domain>/use_cases.py`; expose only `async execute(...)`.
2. Add request and response schemas in `core/<domain>/delivery/fastapi/schemas.py`.
3. Add a controller method in `core/<domain>/delivery/fastapi/controllers.py`.
4. Register the route with a full `/api/v1/...` path.
5. Add the controller to `entrypoints/fastapi/factories.py` if it is a new controller.
6. Cover the controller with an integration test and the use case with a unit test.

Use cases open persistence scopes in `execute(...)` with `async with self._uow as uow`. Pass the active `uow` to focused services when needed, and keep SQLAlchemy access inside core repositories.
