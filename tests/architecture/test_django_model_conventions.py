import ast
from dataclasses import dataclass
from typing import Self

from tests.architecture._source import (
    SourceModule,
    base_names,
    iter_class_definitions,
    iter_source_modules,
    name_for_expression,
)

DJANGO_MODEL_BASE_NAMES = {
    "AbstractBaseUser",
    "AbstractUser",
    "Model",
}
DJANGO_RELATION_FIELD_NAMES = {
    "ForeignKey",
    "ManyToManyField",
    "OneToOneField",
}
DJANGO_TO_ONE_RELATION_FIELD_NAMES = {
    "ForeignKey",
    "OneToOneField",
}


@dataclass(frozen=True)
class ModelField:
    module: SourceModule
    class_node: ast.ClassDef
    name: str
    line_number: int
    call: ast.Call
    annotation: ast.expr | None

    @property
    def field_type_name(self) -> str:
        return _annotation_name(self.call.func)

    @property
    def display_name(self) -> str:
        return f"{self.class_node.name}.{self.name}"

    @classmethod
    def from_statement(
        cls,
        *,
        module: SourceModule,
        class_node: ast.ClassDef,
        statement: ast.stmt,
    ) -> Self | None:
        field_name = _assigned_name(statement)
        field_call = _field_call(statement)

        if field_name is None or field_call is None:
            return None

        return cls(
            module=module,
            class_node=class_node,
            name=field_name,
            line_number=statement.lineno,
            call=field_call,
            annotation=_field_annotation(statement),
        )


def test_django_model_fields_define_verbose_names() -> None:
    violations = [
        _format_field_violation(field)
        for field in _iter_declared_model_fields()
        if not _has_explicit_verbose_name(field)
    ]

    assert violations == [], (
        "Django model fields must define explicit verbose names. "
        "Use verbose_name=... so field declarations stay keyword-only."
    )


def test_django_model_field_calls_use_keyword_arguments() -> None:
    violations = [
        _format_field_violation(field) for field in _iter_declared_model_fields() if field.call.args
    ]

    assert violations == [], (
        "Django model field declarations must use keyword arguments. "
        "Use verbose_name=... and to=... instead of positional arguments."
    )


def test_django_to_one_relation_fields_are_annotated_with_related_model_type() -> None:
    violations = [
        _format_field_violation(field)
        for field in _iter_declared_model_fields()
        if field.field_type_name in DJANGO_TO_ONE_RELATION_FIELD_NAMES
        if not _has_related_model_annotation(field)
    ]

    assert violations == [], (
        "ForeignKey and OneToOneField attributes must be annotated with the related "
        "model type, for example `user: models.ForeignKey[User, User] = "
        "models.ForeignKey(...)`."
    )


def test_django_relation_fields_define_related_name() -> None:
    violations = [
        _format_field_violation(field)
        for field in _iter_declared_model_fields()
        if field.field_type_name in DJANGO_RELATION_FIELD_NAMES
        if not _has_non_empty_keyword(field.call, "related_name")
    ]

    assert violations == [], "Django relationship fields must define explicit related_name values."


def test_django_relation_related_names_are_annotated_on_target_models() -> None:
    model_classes = _model_classes_by_name()
    violations = [
        f"{field.module.relative_path}:{field.line_number} {field.display_name} -> {related_name}"
        for field in _iter_declared_model_fields()
        if field.field_type_name in DJANGO_RELATION_FIELD_NAMES
        if (related_name := _related_name(field)) is not None
        if related_name != "+"
        if (target_model_name := _related_model_name(field)) is not None
        if (target_class := model_classes.get(target_model_name)) is not None
        if _annotation_model_name(_class_attribute_annotation(target_class, related_name))
        != field.class_node.name
    ]

    assert violations == [], (
        "Django relationship related_name values must be annotated on the target model. "
        'For example, `refresh_sessions: models.Manager["RefreshSession"]` on User.'
    )


def test_direct_django_models_define_meta_verbose_names() -> None:
    violations = [
        f"{module.relative_path}:{class_node.lineno} {class_node.name}"
        for module in _iter_model_modules()
        for class_node in iter_class_definitions(module)
        if "Model" in base_names(class_node)
        if not _class_meta_defines(class_node, {"verbose_name", "verbose_name_plural"})
    ]

    assert violations == [], (
        "Concrete Django models that inherit models.Model directly must define "
        "Meta.verbose_name and Meta.verbose_name_plural."
    )


def test_django_models_define_string_representation() -> None:
    violations = [
        f"{module.relative_path}:{class_node.lineno} {class_node.name}"
        for module in _iter_model_modules()
        for class_node in iter_class_definitions(module)
        if _is_concrete_django_model(class_node)
        if "__str__" not in _class_method_names(class_node)
    ]

    assert violations == [], "Concrete Django models must define __str__()."


def _iter_declared_model_fields() -> list[ModelField]:
    return [
        field
        for module in _iter_model_modules()
        for class_node in iter_class_definitions(module)
        if _is_concrete_django_model(class_node)
        for statement in class_node.body
        if (
            field := ModelField.from_statement(
                module=module,
                class_node=class_node,
                statement=statement,
            )
        )
        is not None
    ]


def _iter_model_modules() -> list[SourceModule]:
    return [
        module
        for module in iter_source_modules()
        if module.path.name == "models.py"
        if "migrations" not in module.source_parts
    ]


def _model_classes_by_name() -> dict[str, ast.ClassDef]:
    return {
        class_node.name: class_node
        for module in _iter_model_modules()
        for class_node in iter_class_definitions(module)
        if _is_concrete_django_model(class_node)
    }


def _is_concrete_django_model(class_node: ast.ClassDef) -> bool:
    return not class_node.name.startswith("Base") and not base_names(class_node).isdisjoint(
        DJANGO_MODEL_BASE_NAMES,
    )


def _field_call(statement: ast.stmt) -> ast.Call | None:
    value = statement.value if isinstance(statement, ast.Assign | ast.AnnAssign) else None

    if isinstance(value, ast.Call) and _is_django_field_call(value):
        return value

    return None


def _is_django_field_call(call: ast.Call) -> bool:
    field_type_name = _annotation_name(call.func)
    return field_type_name.endswith("Field") or field_type_name in DJANGO_RELATION_FIELD_NAMES


def _assigned_name(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id

    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
        if isinstance(target, ast.Name):
            return target.id

    return None


def _field_annotation(statement: ast.stmt) -> ast.expr | None:
    if isinstance(statement, ast.AnnAssign):
        return statement.annotation

    return None


def _has_explicit_verbose_name(field: ModelField) -> bool:
    return _has_non_empty_keyword(field.call, "verbose_name")


def _has_related_model_annotation(field: ModelField) -> bool:
    annotation_name = _annotation_model_name(field.annotation)
    expected_name = _related_model_name(field)

    if annotation_name is None:
        return False

    return expected_name is None or annotation_name == expected_name


def _related_name(field: ModelField) -> str | None:
    related_name = _keyword_value(field.call, "related_name")

    if isinstance(related_name, ast.Constant) and isinstance(related_name.value, str):
        return related_name.value

    return None


def _related_model_name(field: ModelField) -> str | None:
    target = _relation_target(field.call)

    if target is None:
        return None

    if _is_auth_user_model_reference(target):
        return "User"

    if isinstance(target, ast.Constant) and isinstance(target.value, str):
        return _model_name_from_string_target(target.value, current_model=field.class_node.name)

    return name_for_expression(target)


def _relation_target(call: ast.Call) -> ast.expr | None:
    if call.args:
        return call.args[0]

    return _keyword_value(call, "to")


def _annotation_model_name(annotation: ast.expr | None) -> str | None:
    if annotation is None:
        return None

    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return _annotation_model_name_from_string(annotation.value)

    if isinstance(annotation, ast.Subscript):
        return _annotation_model_name(annotation.slice)

    if isinstance(annotation, ast.Tuple):
        return _annotation_model_name(annotation.elts[-1]) if annotation.elts else None

    return name_for_expression(annotation)


def _model_name_from_string_target(target: str, *, current_model: str) -> str:
    if target == "self":
        return current_model

    return target.rsplit(".", maxsplit=1)[-1]


def _annotation_model_name_from_string(annotation: str) -> str:
    if "[" in annotation and annotation.endswith("]"):
        annotation = annotation.rsplit("[", maxsplit=1)[-1].removesuffix("]")
        annotation = annotation.rsplit(",", maxsplit=1)[-1].strip()
        annotation = annotation.strip("\"'")

    return annotation.rsplit(".", maxsplit=1)[-1]


def _is_auth_user_model_reference(expression: ast.expr) -> bool:
    return (
        isinstance(expression, ast.Attribute)
        and expression.attr == "AUTH_USER_MODEL"
        and isinstance(expression.value, ast.Name)
        and expression.value.id == "settings"
    )


def _has_non_empty_keyword(call: ast.Call, keyword_name: str) -> bool:
    value = _keyword_value(call, keyword_name)

    if value is None:
        return False

    return not (isinstance(value, ast.Constant) and value.value == "")


def _keyword_value(call: ast.Call, keyword_name: str) -> ast.expr | None:
    return next(
        (keyword.value for keyword in call.keywords if keyword.arg == keyword_name),
        None,
    )


def _class_attribute_annotation(class_node: ast.ClassDef, attribute_name: str) -> ast.expr | None:
    for statement in class_node.body:
        if (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == attribute_name
        ):
            return statement.annotation

    return None


def _class_meta_defines(class_node: ast.ClassDef, required_names: set[str]) -> bool:
    meta_class = next(
        (
            statement
            for statement in class_node.body
            if isinstance(statement, ast.ClassDef)
            if statement.name == "Meta"
        ),
        None,
    )

    if meta_class is None:
        return False

    defined_names = {
        statement_name
        for statement in meta_class.body
        if isinstance(statement, ast.Assign | ast.AnnAssign)
        if (statement_name := _assigned_name(statement)) is not None
    }
    return required_names.issubset(defined_names)


def _class_method_names(class_node: ast.ClassDef) -> set[str]:
    return {
        statement.name
        for statement in class_node.body
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _annotation_name(annotation: ast.expr) -> str:
    return name_for_expression(annotation) or ""


def _format_field_violation(field: ModelField) -> str:
    return f"{field.module.relative_path}:{field.line_number} {field.display_name}"
