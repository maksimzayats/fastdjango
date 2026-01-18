from punq import Container, Scope

from delivery.http.factories import FastAPIFactory


class Registry:
    def register(self, container: Container) -> None:
        container.register(
            "FastAPIFactory",
            factory=lambda: container.resolve(FastAPIFactory),
            scope=Scope.singleton,
        )
