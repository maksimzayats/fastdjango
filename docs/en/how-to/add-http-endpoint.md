# Add an HTTP Endpoint

1. Add or choose a scoped use case file in `core/<domain>/use_cases/`; expose only `async execute(...)`.
2. Add scoped request and response schema files in `core/<domain>/delivery/fastapi/schemas/`.
3. Add one endpoint/action controller file in `core/<domain>/delivery/fastapi/controllers/`.
4. Register the route with a full `/api/v1/...` path.
5. Add the controller to `entrypoints/fastapi/factory.py` if it is a new controller.
6. Cover the controller with an integration test and the use case with a unit test.

Request schemas are delivery shapes, not DTOs. The controller maps request
schema fields into a DTO, calls one use case, and maps the result to a response
schema.

Do not add aggregate modules or package re-exports for new endpoints. Import
the use case, DTO, schema, and controller from their direct scoped modules.

Use cases open unit-of-work scopes in `execute(...)` with `async with self._uow as uow` when database access is needed. Pass the active `uow` to focused services when needed, and keep SQLAlchemy work inside the local infrastructure repository implementation.
