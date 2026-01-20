from configs.logging import LoggingConfigurator
from infrastructure.frameworks.django.configurator import DjangoConfigurator
from infrastructure.frameworks.logfire.instrumentor import OpenTelemetryInstrumentor
from infrastructure.frameworks.punq.auto_registering import AutoRegisteringContainer


class ContainerFactory:
    def __call__(
        self,
        *,
        configure_django: bool = True,
        configure_logging: bool = True,
        instrument_libraries: bool = True,
    ) -> AutoRegisteringContainer:
        container = AutoRegisteringContainer()

        # It's required to configure Django before any registrations due to model imports
        if configure_django:
            self._configure_django(container)

        if configure_logging:
            self._configure_logging(container)

        if instrument_libraries:
            self._instrument_libraries(container)

        self._register(container)

        return container

    def _configure_django(self, container: AutoRegisteringContainer) -> None:
        configurator = container.resolve(DjangoConfigurator)
        configurator.configure(django_settings_module="configs.django")

    def _configure_logging(self, container: AutoRegisteringContainer) -> None:
        configurator = container.resolve(LoggingConfigurator)
        configurator.configure()

    def _instrument_libraries(self, container: AutoRegisteringContainer) -> None:
        instrumentor = container.resolve(OpenTelemetryInstrumentor)
        instrumentor.instrument_libraries()

    def _register(self, container: AutoRegisteringContainer) -> None:
        # Import registry functions here to avoid imports before setting up Django
        from ioc.registries import Registry  # noqa: PLC0415

        registry = container.resolve(Registry)
        registry.register(container)
