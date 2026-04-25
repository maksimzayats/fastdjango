"""Django's command-line utility for administrative tasks."""

import sys

from django.core.management import execute_from_command_line

from fastdjango.ioc.container import get_container


class DjangoManager:
    def execute_from_command_line(self, argv: list[str]) -> None:
        execute_from_command_line(argv)


def main() -> None:
    container = get_container()

    manager = container.resolve(DjangoManager)
    manager.execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
