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
    repo_url: str | None


def replace_project_references(text: str, *, references: ProjectReferences) -> str:
    old_package_name = references.old_package_name
    new_package_name = references.new_package_name
    project_name = references.project_name
    docs_site_url = references.docs_site_url
    repo_url = references.repo_url

    rewritten = _replace_docs_site_references(text=text, docs_site_url=docs_site_url)
    rewritten = _replace_repository_references(text=rewritten, repo_url=repo_url)
    rewritten = rewritten.replace(f"src/{old_package_name}", f"src/{new_package_name}")
    rewritten = _replace_token(
        text=rewritten,
        old_value=old_package_name,
        new_value=new_package_name,
    )
    rewritten = rewritten.replace("FastAPI Template", project_name)
    return rewritten.replace("FastAPITemplate", project_name.replace(" ", ""))


def _replace_token(*, text: str, old_value: str, new_value: str) -> str:
    return re.sub(
        pattern=rf"\b{re.escape(old_value)}\b",
        repl=new_value,
        string=text,
    )


def _replace_docs_site_references(*, text: str, docs_site_url: str | None) -> str:
    if docs_site_url is None:
        return text.replace("https://fastapi-template.zayats.dev", "docs/en").replace(
            "fastapi-template.zayats.dev",
            "local docs",
        )

    normalized_docs_site_url = docs_site_url.rstrip("/")
    docs_site_host = urlsplit(normalized_docs_site_url).netloc or normalized_docs_site_url
    return text.replace("https://fastapi-template.zayats.dev", normalized_docs_site_url).replace(
        "fastapi-template.zayats.dev",
        docs_site_host,
    )


def _replace_repository_references(*, text: str, repo_url: str | None) -> str:
    template_repo_url = "https://github.com/maksimzayats/fastapi-template"
    if repo_url is not None:
        return text.replace(template_repo_url, repo_url.removesuffix(".git").rstrip("/"))

    return re.sub(
        pattern=rf"\[([^\]]+)\]\({re.escape(template_repo_url)}(?:/[^\)]*)?\)",
        repl=r"\1",
        string=text,
    ).replace(template_repo_url, "your repository")
