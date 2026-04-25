from diwire import Container, DependencyRegistrationPolicy, MissingPolicy

from fastdjango.infrastructure.django.configurator import DjangoConfigurator
from fastdjango.infrastructure.logfire.configurator import LogfireConfigurator
from fastdjango.infrastructure.logfire.instrumentor import OpenTelemetryInstrumentor
from fastdjango.infrastructure.logging.configurator import LoggingConfigurator
from fastdjango.ioc.registry import register_dependencies


def get_container(
    *,
    configure_django: bool = True,
    configure_logging: bool = True,
    configure_logfire: bool = True,
    instrument_libraries: bool = True,
) -> Container:
    container = Container(
        missing_policy=MissingPolicy.REGISTER_RECURSIVE,
        dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE,
    )

    # Django must be configured before dependency resolution touches model imports.
    if configure_django:
        _configure_django(container)

    if configure_logging:
        _configure_logging(container)

    if configure_logfire:
        _configure_logfire(container)

    if instrument_libraries:
        _instrument_libraries(container)

    register_dependencies(container)

    return container


def _configure_django(container: Container) -> None:
    configurator = container.resolve(DjangoConfigurator)
    configurator.configure()


def _configure_logging(container: Container) -> None:
    configurator = container.resolve(LoggingConfigurator)
    configurator.configure()


def _configure_logfire(container: Container) -> None:
    configurator = container.resolve(LogfireConfigurator)
    configurator.configure()


def _instrument_libraries(container: Container) -> None:
    instrumentor = container.resolve(OpenTelemetryInstrumentor)
    instrumentor.instrument_libraries()
