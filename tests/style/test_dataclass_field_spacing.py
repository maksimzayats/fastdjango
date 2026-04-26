import ast
from dataclasses import dataclass
from itertools import pairwise

from tests.architecture._source import (
    has_dataclass_kw_only_decorator,
    is_classvar_annotation,
    is_injected_annotation,
    iter_class_definitions,
    iter_source_modules,
)


@dataclass(frozen=True)
class DataclassField:
    name: str
    line_number: int
    end_line_number: int
    is_injected: bool


def test_injected_fields_are_separated_from_other_fields() -> None:
    violations: list[str] = []

    for module in iter_source_modules():
        lines = module.path.read_text(encoding="utf-8").splitlines()

        for class_node in iter_class_definitions(module):
            if not has_dataclass_kw_only_decorator(class_node):
                continue

            fields = list(_iter_dataclass_fields(class_node))

            violations.extend(
                (
                    f"{module.relative_path}:{next_field.line_number} "
                    f"{class_node.name}.{next_field.name}"
                )
                for previous_field, next_field in pairwise(fields)
                if previous_field.is_injected != next_field.is_injected
                if not _has_empty_line_between(
                    lines=lines,
                    previous_field=previous_field,
                    next_field=next_field,
                )
            )

    assert violations == [], (
        "Injected dependency fields must be separated from other dataclass fields by an empty line."
    )


def _iter_dataclass_fields(class_node: ast.ClassDef) -> list[DataclassField]:
    return [
        DataclassField(
            name=field_node.target.id,
            line_number=field_node.lineno,
            end_line_number=field_node.end_lineno or field_node.lineno,
            is_injected=is_injected_annotation(field_node.annotation),
        )
        for field_node in class_node.body
        if isinstance(field_node, ast.AnnAssign)
        if isinstance(field_node.target, ast.Name)
        if not is_classvar_annotation(field_node.annotation)
    ]


def _has_empty_line_between(
    *,
    lines: list[str],
    previous_field: DataclassField,
    next_field: DataclassField,
) -> bool:
    return any(
        not line.strip()
        for line in lines[previous_field.end_line_number : next_field.line_number - 1]
    )
