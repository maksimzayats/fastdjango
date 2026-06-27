from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modern_python_template.core.user"
    label = "user"

    def ready(self) -> None:
        from modern_python_template.core.user.delivery.django import (  # noqa: PLC0415
            admin as _user_admin,  # noqa: F401
        )
