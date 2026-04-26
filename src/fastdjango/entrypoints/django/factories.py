from dataclasses import dataclass

from diwire import Injected
from django.contrib.admin import AdminSite
from django.contrib.admin.sites import site as default_site
from django.core.handlers.wsgi import WSGIHandler

from fastdjango.foundation.factories import BaseFactory


@dataclass(kw_only=True)
class AdminSiteFactory(BaseFactory):
    def __call__(self) -> AdminSite:
        return default_site


@dataclass(kw_only=True)
class DjangoWSGIFactory(BaseFactory):
    _admin_site_factory: Injected[AdminSiteFactory]

    def __call__(self) -> WSGIHandler:
        self._admin_site_factory()

        return WSGIHandler()
