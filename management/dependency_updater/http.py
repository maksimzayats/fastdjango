import json
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from management.dependency_updater.json_response import JsonResponse


def _json_response(*, url: str, headers: dict[str, str] | None = None) -> JsonResponse | None:
    if urlparse(url).scheme != "https":
        return None

    http_request = Request(  # noqa: S310
        url,
        headers=headers or {},
    )
    try:
        with urlopen(http_request, timeout=10) as response:  # noqa: S310
            return JsonResponse(
                payload=json.load(response),
                link=response.headers.get("Link"),
            )
    except (
        OSError,
        URLError,
        json.JSONDecodeError,
    ):
        return None
