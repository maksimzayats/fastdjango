from diwire import Container, DependencyRegistrationPolicy, MissingPolicy

from fastapi_template.infrastructure.logfire.configurator import LogfireConfigurator
from fastapi_template.infrastructure.logfire.instrumentor import OpenTelemetryInstrumentor
from fastapi_template.infrastructure.logging.configurator import LoggingConfigurator
from fastapi_template.ioc.registry import register_dependencies


def get_container(
    *,
    configure_logging: bool = True,
    configure_logfire: bool = True,
    instrument_libraries: bool = True,
) -> Container:
    """Build the dependency injection container and bootstrap integrations.

    Returns:
        Configured ``diwire`` container for the application.
    """
    container = Container(
        missing_policy=MissingPolicy.REGISTER_RECURSIVE,
        dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE,
    )

    register_dependencies(container)

    if configure_logging:
        _configure_logging(container)

    if configure_logfire:
        _configure_logfire(container)

    if instrument_libraries:
        _instrument_libraries(container)

    return container


def _configure_logging(container: Container) -> None:
    configurator = container.resolve(LoggingConfigurator)
    configurator.configure()


def _configure_logfire(container: Container) -> None:
    configurator = container.resolve(LogfireConfigurator)
    configurator.configure()


def _instrument_libraries(container: Container) -> None:
    instrumentor = container.resolve(OpenTelemetryInstrumentor)
    instrumentor.instrument_libraries()
