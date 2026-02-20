from diwire import Container, DependencyRegistrationPolicy, MissingPolicy

from configs.logging import LoggingConfigurator
from infrastructure.frameworks.django.configurator import DjangoConfigurator
from infrastructure.frameworks.logfire.instrumentor import OpenTelemetryInstrumentor


class ContainerFactory:
    def __call__(
        self,
        *,
        configure_django: bool = True,
        configure_logging: bool = True,
        instrument_libraries: bool = True,
    ) -> Container:
        container = Container(
            missing_policy=MissingPolicy.REGISTER_RECURSIVE,
            dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE,
        )

        # It's required to configure Django before any registrations due to model imports
        if configure_django:
            self._configure_django(container)

        if configure_logging:
            self._configure_logging(container)

        if instrument_libraries:
            self._instrument_libraries(container)

        return container

    def _configure_django(self, container: Container) -> None:
        configurator = container.resolve(DjangoConfigurator)
        configurator.configure(django_settings_module="configs.django")

    def _configure_logging(self, container: Container) -> None:
        configurator = container.resolve(LoggingConfigurator)
        configurator.configure()

    def _instrument_libraries(self, container: Container) -> None:
        instrumentor = container.resolve(OpenTelemetryInstrumentor)
        instrumentor.instrument_libraries()
