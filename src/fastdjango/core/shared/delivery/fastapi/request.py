import ipaddress
import logging
from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected
from pydantic_settings import BaseSettings
from starlette.requests import Request

from fastdjango.foundation.services import BaseService

logger = logging.getLogger(__name__)

type IPAddressTrace = tuple[str, ...]


class RequestInfoServiceSettings(BaseSettings):
    ip_header: str = "x-forwarded-for"
    """Header containing the forwarded IP address trace when behind proxies."""

    user_agent_header: str = "user-agent"
    """Header to look for the user agent string."""


@dataclass(kw_only=True)
class RequestInfoService(BaseService):
    INVALID_IP_ADDRESS_ERROR: ClassVar = ValueError

    _settings: Injected[RequestInfoServiceSettings]

    def get_user_agent(self, request: Request) -> str:
        return request.headers.get(self._settings.user_agent_header, "")

    def get_user_ip_trace(self, request: Request) -> str | None:
        header_value = request.headers.get(self._settings.ip_header)
        if header_value is None:
            return self._get_remote_address(request=request)

        addresses = self._parse_ip_trace(header_value)
        if addresses:
            return ",".join(addresses)

        logger.warning(
            "Forwarded IP header %s does not contain a valid IP trace: %s",
            self._settings.ip_header,
            header_value,
        )
        return self._get_remote_address(request=request)

    def _get_remote_address(self, request: Request) -> str | None:
        client = request.client
        remote_address = client[0] if client else None
        if remote_address is None:
            return None

        normalized_address = self._normalize_ip(remote_address)
        if normalized_address is not None:
            return normalized_address

        logger.warning("Remote address is not a valid IP: %s", remote_address)
        return None

    def _parse_ip_trace(self, value: str) -> IPAddressTrace:
        addresses: list[str] = []
        for raw_address in value.split(","):
            address = raw_address.strip()
            if not address:
                return ()

            normalized_address = self._normalize_ip(address)
            if normalized_address is None:
                return ()

            addresses.append(normalized_address)

        return tuple(addresses)

    def _normalize_ip(self, address: str) -> str | None:
        try:
            ip = ipaddress.ip_address(address)
        except self.INVALID_IP_ADDRESS_ERROR:
            return None
        else:
            return str(ip)
