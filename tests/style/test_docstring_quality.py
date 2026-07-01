import ast
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tests.architecture._source import REPO_ROOT, SOURCE_ROOT

MANAGEMENT_ROOT = REPO_ROOT / "management"
DOCSTRING_ALLOWLIST: dict[str, str] = {}
PLACEHOLDER_PATTERNS = (
    re.compile(r"^Define\s+[A-Za-z_][\w]*(?:\.|$)"),
    re.compile(r"^Run\s+[A-Za-z_][\w\s-]*(?:\.|$)"),
    re.compile(r"^Initialize the (?:instance|middleware|progress reporter)\.$"),
    re.compile(r"^Base class for .+ implementations\.$"),
    re.compile(r"^(?:Return|Returns) the operation result\.$"),
    re.compile(r"^The operation result\.$"),
    re.compile(
        r"^(?:Create|Get|Set|Build|Configure|Execute|Return|Check|Validate|Map|Convert|"
        r"Load|Make|Generate|Issue|Refresh|Revoke|Hash|Verify|Normalize)\s+"
        r"(?:a|an|the)?\s*[A-Za-z_][\w-]*(?:\s+[A-Za-z_][\w-]*){0,2}\.$",
    ),
)
PLACEHOLDER_BODY_PATTERNS = (re.compile(r"(?m)^\s*The operation result\.\s*$"),)
ACTION_WORDS = frozenset(
    (
        "build",
        "check",
        "configure",
        "convert",
        "create",
        "define",
        "execute",
        "generate",
        "get",
        "hash",
        "initialize",
        "issue",
        "load",
        "make",
        "map",
        "normalize",
        "refresh",
        "return",
        "revoke",
        "run",
        "set",
        "validate",
        "verify",
    ),
)
GENERIC_WORDS = frozenset(
    (
        "a",
        "an",
        "class",
        "data",
        "instance",
        "method",
        "object",
        "the",
    ),
)


@dataclass(frozen=True)
class DocstringCandidate:
    qualified_name: str
    relative_path: Path
    line_number: int
    object_name: str
    docstring: str


def test_project_docstrings_are_not_placeholder_text() -> None:
    violations = _placeholder_docstring_violations(candidates=_iter_project_docstrings())

    assert violations == [], "Docstrings must explain behavior, contracts, or boundaries."


def test_docstring_guardrail_rejects_define_name_placeholders() -> None:
    tree = ast.parse('class AuthenticatedRequest:\n    """Define AuthenticatedRequest."""\n')

    assert _fake_module_violations(tree=tree) == [
        "example.py:2 example.AuthenticatedRequest: Define AuthenticatedRequest.",
    ]


def test_docstring_guardrail_rejects_run_method_placeholders() -> None:
    tree = ast.parse('def execute():\n    """Run execute."""\n')

    assert _fake_module_violations(tree=tree) == [
        "example.py:2 example.execute: Run execute.",
    ]


def test_docstring_guardrail_rejects_operation_result_sections() -> None:
    tree = ast.parse(
        '''
def issue_token():
    """Issue token.

    Returns:
        The operation result.
    """
''',
    )

    assert _fake_module_violations(tree=tree) == [
        "example.py:3 example.issue_token: Issue token.",
    ]


def test_docstring_guardrail_rejects_normalized_name_restatements() -> None:
    tree = ast.parse(
        'class RefreshSessionRepository:\n    """Refresh session repository."""\n',
    )

    assert _fake_module_violations(tree=tree) == [
        "example.py:2 example.RefreshSessionRepository: Refresh session repository.",
    ]


def test_docstring_guardrail_allows_contract_docstrings() -> None:
    tree = ast.parse(
        '''
class RefreshSessionRepository:
    """Persistence port for refresh-session lifecycle operations."""
''',
    )

    assert _fake_module_violations(tree=tree) == []


def _fake_module_violations(*, tree: ast.Module) -> list[str]:
    return _placeholder_docstring_violations(
        candidates=_iter_docstrings(
            tree=tree,
            module_name="example",
            relative_path=Path("example.py"),
        ),
    )


def _placeholder_docstring_violations(
    *,
    candidates: Iterable[DocstringCandidate],
) -> list[str]:
    return [
        (
            f"{candidate.relative_path}:{candidate.line_number} "
            f"{candidate.qualified_name}: {_first_sentence(candidate.docstring)}"
        )
        for candidate in candidates
        if candidate.qualified_name not in DOCSTRING_ALLOWLIST
        if _is_placeholder_docstring(candidate=candidate)
    ]


def _is_placeholder_docstring(*, candidate: DocstringCandidate) -> bool:
    first_sentence = _first_sentence(candidate.docstring)

    return (
        any(pattern.search(first_sentence) for pattern in PLACEHOLDER_PATTERNS)
        or any(pattern.search(candidate.docstring) for pattern in PLACEHOLDER_BODY_PATTERNS)
        or _is_name_restatement(
            first_sentence=first_sentence,
            object_name=candidate.object_name,
        )
    )


def _iter_project_docstrings() -> Iterable[DocstringCandidate]:
    for root in (SOURCE_ROOT, MANAGEMENT_ROOT):
        for path in sorted(root.rglob("*.py")):
            yield from _iter_docstrings(
                tree=ast.parse(path.read_text(encoding="utf-8"), filename=str(path)),
                module_name=_module_name(path=path),
                relative_path=path.relative_to(REPO_ROOT),
            )


def _iter_docstrings(
    *,
    tree: ast.Module,
    module_name: str,
    relative_path: Path,
) -> Iterable[DocstringCandidate]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        docstring = ast.get_docstring(node, clean=False)
        if docstring is None:
            continue

        yield DocstringCandidate(
            qualified_name=f"{module_name}.{node.name}",
            relative_path=relative_path,
            line_number=node.body[0].lineno,
            object_name=node.name,
            docstring=docstring.strip(),
        )


def _module_name(*, path: Path) -> str:
    if path.is_relative_to(SOURCE_ROOT):
        module_path = path.relative_to(SOURCE_ROOT).with_suffix("")
        return f"fastapi_template.{'.'.join(module_path.parts)}"

    module_path = path.relative_to(REPO_ROOT).with_suffix("")
    return ".".join(module_path.parts)


def _is_name_restatement(*, first_sentence: str, object_name: str) -> bool:
    sentence_terms = _meaningful_terms(first_sentence)
    name_terms = _meaningful_terms(object_name)

    return bool(sentence_terms) and sentence_terms == name_terms


def _meaningful_terms(value: str) -> tuple[str, ...]:
    return tuple(
        term for term in _terms(value) if term not in ACTION_WORDS if term not in GENERIC_WORDS
    )


def _terms(value: str) -> tuple[str, ...]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    expanded = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", expanded)

    return tuple(term.casefold() for term in re.findall(r"[A-Za-z0-9]+", expanded) if term)


def _first_sentence(docstring: str) -> str:
    return docstring.strip().splitlines()[0].strip()
