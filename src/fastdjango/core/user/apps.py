from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fastdjango.core.user"
    label = "user"

    def ready(self) -> None:
        from fastdjango.core.user.delivery.django import admin as _user_admin  # noqa: F401, I001, PLC0415
