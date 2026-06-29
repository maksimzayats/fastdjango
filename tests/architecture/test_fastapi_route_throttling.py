import ast
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi_template.entrypoints.fastapi.factory import PRE_BODY_IP_THROTTLED_ROUTES
from tests.architecture._source import SourceModule, iter_source_modules

POST_METHOD = "POST"


def test_pre_body_ip_throttling_covers_real_public_post_routes() -> None:
    public_post_routes = {
        route.path
        for module in _fastapi_controller_modules()
        for route in _registered_api_routes(module=module)
        if route.path.startswith("/api/v1") and POST_METHOD in route.methods
    }
    throttled_post_routes = {
        path for method, path in PRE_BODY_IP_THROTTLED_ROUTES if method == POST_METHOD
    }

    assert public_post_routes == throttled_post_routes


def _fastapi_controller_modules() -> Iterable[SourceModule]:
    for module in iter_source_modules():
        source_parts = module.source_parts
        if "delivery" not in source_parts:
            continue

        if source_parts[-3:] == ("fastapi", "controllers", f"{module.path.stem}.py"):
            yield module


def _registered_api_routes(*, module: SourceModule) -> Iterable[RegisteredRoute]:
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_api_route":
            continue

        path = _path_value(call=node)
        methods = _methods_value(call=node)
        if path is not None and methods:
            yield RegisteredRoute(path=path, methods=methods)


def _path_value(*, call: ast.Call) -> str | None:
    path_keyword = _keyword(call=call, name="path")
    if path_keyword is not None:
        return _string_value(path_keyword.value)

    if call.args:
        return _string_value(call.args[0])

    return None


def _methods_value(*, call: ast.Call) -> frozenset[str]:
    methods_keyword = _keyword(call=call, name="methods")
    if methods_keyword is None:
        return frozenset()

    if not isinstance(methods_keyword.value, ast.List | ast.Tuple):
        return frozenset()

    return frozenset(
        value
        for method in methods_keyword.value.elts
        if (value := _string_value(method)) is not None
    )


def _keyword(*, call: ast.Call, name: str) -> ast.keyword | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword

    return None


def _string_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    return None


@dataclass(frozen=True, slots=True)
class RegisteredRoute:
    path: str
    methods: frozenset[str]
