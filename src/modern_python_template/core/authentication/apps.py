from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modern_python_template.core.authentication"
    label = "authentication"

    def ready(self) -> None:
        from modern_python_template.core.authentication.delivery.django import (  # noqa: PLC0415
            admin as _auth_admin,  # noqa: F401
        )
