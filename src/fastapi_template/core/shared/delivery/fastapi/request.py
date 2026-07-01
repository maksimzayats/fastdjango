import ipaddress
import logging
from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected
from pydantic_settings import BaseSettings
from starlette.requests import Request

from fastapi_template.foundation.service import BaseService

logger = logging.getLogger(__name__)

type IPAddressTrace = tuple[str, ...]


class RequestInfoServiceSettings(BaseSettings):
    """Header settings used to derive request identity metadata."""

    ip_header: str = "x-forwarded-for"
    """Header containing the forwarded IP address trace when behind proxies."""

    trust_forwarded_ip_header: bool = False
    """Whether to trust the forwarded IP header for client identity."""

    user_agent_header: str = "user-agent"
    """Header to look for the user agent string."""


@dataclass(kw_only=True)
class RequestInfoService(BaseService):
    """Extract user-agent and client IP trace from FastAPI requests."""

    INVALID_IP_ADDRESS_ERROR: ClassVar = ValueError  # noqa: WPS115

    _settings: Injected[RequestInfoServiceSettings]

    def get_user_agent(self, *, request: Request) -> str:
        """Read the configured user-agent header from a request.

        Returns:
            User-agent header value, or an empty string when absent.
        """
        return request.headers.get(self._settings.user_agent_header, "")

    def get_user_ip_trace(self, *, request: Request) -> str | None:
        """Resolve the trusted client IP trace for throttling and audit data.

        Returns:
            Normalized comma-separated IP trace, or ``None`` when unavailable.
        """
        if not self._settings.trust_forwarded_ip_header:
            return self._get_remote_address(request=request)

        header_value = request.headers.get(self._settings.ip_header)
        if header_value is None:
            return self._get_remote_address(request=request)

        addresses = self._parse_ip_trace(header_value=header_value)
        if addresses:
            return ",".join(addresses)

        logger.warning(
            "Forwarded IP header %s does not contain a valid IP trace: %s",
            self._settings.ip_header,
            header_value,
        )
        return self._get_remote_address(request=request)

    def _get_remote_address(self, *, request: Request) -> str | None:
        client = request.client
        remote_address = client[0] if client else None
        if remote_address is None:
            return None

        normalized_address = self._normalize_ip(address=remote_address)
        if normalized_address is not None:
            return normalized_address

        logger.warning("Remote address is not a valid IP: %s", remote_address)
        return None

    def _parse_ip_trace(self, *, header_value: str) -> IPAddressTrace:
        addresses: list[str] = []
        for raw_address in header_value.split(","):
            address = raw_address.strip()
            if not address:
                return ()

            normalized_address = self._normalize_ip(address=address)
            if normalized_address is None:
                return ()

            addresses.append(normalized_address)

        return tuple(addresses)

    def _normalize_ip(self, *, address: str) -> str | None:
        try:
            ip = ipaddress.ip_address(address)
        except self.INVALID_IP_ADDRESS_ERROR:
            return None
        else:
            return str(ip)
