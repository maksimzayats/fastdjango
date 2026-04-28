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


@dataclass(frozen=True)
class ClassStatement:
    name: str
    line_number: int
    end_line_number: int
    is_exception_contract: bool


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
                    previous_end_line_number=previous_field.end_line_number,
                    next_line_number=next_field.line_number,
                )
            )

    assert violations == [], (
        "Injected dependency fields must be separated from other dataclass fields by an empty line."
    )


def test_exception_contract_classvars_are_separated_from_other_class_members() -> None:
    violations: list[str] = []

    for module in iter_source_modules():
        lines = module.path.read_text(encoding="utf-8").splitlines()

        for class_node in iter_class_definitions(module):
            statements = list(_iter_class_statements(class_node))

            violations.extend(
                (
                    f"{module.relative_path}:{next_statement.line_number} "
                    f"{class_node.name}.{next_statement.name}"
                )
                for previous_statement, next_statement in pairwise(statements)
                if previous_statement.is_exception_contract
                if not next_statement.is_exception_contract
                if not _has_empty_line_between(
                    lines=lines,
                    previous_end_line_number=previous_statement.end_line_number,
                    next_line_number=next_statement.line_number,
                )
            )

    assert violations == [], (
        "Exception contract ClassVars must be separated from other class members by an empty line."
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


def _iter_class_statements(class_node: ast.ClassDef) -> list[ClassStatement]:
    return [
        ClassStatement(
            name=_class_statement_name(statement),
            line_number=statement.lineno,
            end_line_number=statement.end_lineno or statement.lineno,
            is_exception_contract=_is_exception_contract_classvar(statement),
        )
        for statement in class_node.body
        if not _is_docstring_statement(statement)
    ]


def _has_empty_line_between(
    *,
    lines: list[str],
    previous_end_line_number: int,
    next_line_number: int,
) -> bool:
    return any(not line.strip() for line in lines[previous_end_line_number : next_line_number - 1])


def _is_exception_contract_classvar(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and _is_exception_contract_name(statement.target.id)
        and is_classvar_annotation(statement.annotation)
    )


def _is_exception_contract_name(name: str) -> bool:
    return name.endswith(("_ERROR", "_EXCEPTION"))


def _is_docstring_statement(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _class_statement_name(statement: ast.stmt) -> str:
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id

    if isinstance(statement, ast.Assign):
        targets = [target.id for target in statement.targets if isinstance(target, ast.Name)]
        if targets:
            return ", ".join(targets)

    if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return statement.name

    return statement.__class__.__name__
