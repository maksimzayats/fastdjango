from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, kw_only=True)
class ProjectReferences:
    old_package_name: str
    new_package_name: str
    project_name: str
    docs_site_url: str | None


def replace_project_references(text: str, *, references: ProjectReferences) -> str:
    old_package_name = references.old_package_name
    new_package_name = references.new_package_name
    project_name = references.project_name
    docs_site_url = references.docs_site_url

    rewritten = _replace_docs_site_references(text=text, docs_site_url=docs_site_url)
    rewritten = rewritten.replace(f"src/{old_package_name}/manage.py", "management/manage.py")
    rewritten = rewritten.replace(f"src/{old_package_name}", f"src/{new_package_name}")
    rewritten = _replace_token(
        text=rewritten,
        old_value=old_package_name,
        new_value=new_package_name,
    )
    rewritten = rewritten.replace("Fast Django", project_name)
    return rewritten.replace("FastDjango", project_name.replace(" ", ""))


def _replace_token(*, text: str, old_value: str, new_value: str) -> str:
    return re.sub(
        pattern=rf"\b{re.escape(old_value)}\b",
        repl=new_value,
        string=text,
    )


def _replace_docs_site_references(*, text: str, docs_site_url: str | None) -> str:
    if docs_site_url is None:
        return text.replace("https://fastdjango.zayats.dev", "docs/en").replace(
            "fastdjango.zayats.dev",
            "local docs",
        )

    normalized_docs_site_url = docs_site_url.rstrip("/")
    docs_site_host = urlsplit(normalized_docs_site_url).netloc or normalized_docs_site_url
    return text.replace("https://fastdjango.zayats.dev", normalized_docs_site_url).replace(
        "fastdjango.zayats.dev",
        docs_site_host,
    )
