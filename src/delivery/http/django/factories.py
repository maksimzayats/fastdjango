from dataclasses import dataclass

from django.contrib.admin import AdminSite
from django.contrib.admin.sites import site as default_site
from django.core.handlers.wsgi import WSGIHandler


class AdminSiteFactory:
    def __call__(self) -> AdminSite:
        from delivery.http.controllers.user import admin as _user_admin  # noqa: F401, PLC0415

        return default_site


@dataclass(kw_only=True)
class DjangoWSGIFactory:
    _admin_site_factory: AdminSiteFactory

    def __call__(self) -> WSGIHandler:
        self._admin_site_factory()

        return WSGIHandler()
