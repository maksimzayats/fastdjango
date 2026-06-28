# Dependency Injection

The `diwire` container is created in `fastapi_template.ioc.container`.

Most concrete classes are resolved recursively. Explicit registrations live in `fastapi_template.ioc.registry` when an abstraction must map to an implementation, such as:

- `UnitOfWork` to `SQLAlchemyUnitOfWork`

Application classes receive dependencies through constructor fields annotated with `Injected[...]`.
