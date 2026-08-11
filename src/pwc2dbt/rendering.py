import re

from .graph import TargetAncestry, resolve_source_refs
from .model import Connector, PowerCenterDocument, Transformation


class RenderingError(ValueError):
    """A reached transformation cannot be rendered within the supported slice."""


def _sql_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_").lower()


def _transformation(
    document: PowerCenterDocument,
    ancestry: TargetAncestry,
    instance_name: str,
) -> Transformation:
    mapping = document.mappings[ancestry.mapping_name]
    instance = ancestry.instances[instance_name]
    return mapping.transformations[instance.transformation_name]


def _incoming(ancestry: TargetAncestry, instance_name: str) -> tuple[Connector, ...]:
    return tuple(
        connector
        for connector in ancestry.connectors
        if connector.to_instance == instance_name
    )


def _downstream_fields(
    ancestry: TargetAncestry, instance_name: str
) -> set[str]:
    return {
        connector.from_field
        for connector in ancestry.connectors
        if connector.from_instance == instance_name
    }


def _render_source_qualifier(
    document: PowerCenterDocument,
    ancestry: TargetAncestry,
    instance_name: str,
    transformation: Transformation,
) -> str:
    for attribute_name in (
        "Sql Query",
        "User Defined Join",
        "Source Filter",
        "Pre SQL",
        "Post SQL",
    ):
        value = transformation.table_attributes.get(attribute_name, "")
        if value:
            raise ValueError(f"{attribute_name}='{value}' is not supported")
    if transformation.table_attributes.get("Select Distinct") != "NO":
        raise ValueError("Select Distinct must be NO")
    if transformation.table_attributes.get("Number Of Sorted Ports") != "0":
        raise ValueError("Number Of Sorted Ports must be 0")

    incoming = _incoming(ancestry, instance_name)
    source_names = {connector.from_instance for connector in incoming}
    if len(source_names) != 1:
        raise ValueError(
            f"Source Qualifier '{instance_name}' requires exactly one source instance"
        )

    source_name = next(iter(source_names))
    source_ref = resolve_source_refs(document, ancestry)[source_name]
    incoming_by_field = {connector.to_field: connector for connector in incoming}
    downstream_fields = _downstream_fields(ancestry, instance_name)
    projections = []
    for field in transformation.fields:
        if field.name not in downstream_fields:
            continue
        connector = incoming_by_field[field.name]
        source_field = _sql_name(connector.from_field)
        output_field = _sql_name(field.name)
        projections.append(
            source_field
            if source_field == output_field
            else f"{source_field} AS {output_field}"
        )

    return "SELECT\n    " + ",\n    ".join(projections) + f"\nFROM {source_ref}"


def _render_aggregator(
    ancestry: TargetAncestry,
    instance_name: str,
    transformation: Transformation,
) -> str:
    if transformation.table_attributes.get("Sorted Input") != "NO":
        raise ValueError("Sorted Input must be NO")

    upstream_names = {
        connector.from_instance for connector in _incoming(ancestry, instance_name)
    }
    if len(upstream_names) != 1:
        raise ValueError(
            f"Aggregator '{instance_name}' requires exactly one upstream instance"
        )

    downstream_fields = _downstream_fields(ancestry, instance_name)
    projections: list[str] = []
    group_by: list[str] = []
    for field in transformation.fields:
        if field.name not in downstream_fields:
            continue
        if field.expression_type == "GROUPBY":
            expression = _sql_name(field.expression)
            group_by.append(expression)
            projections.append(expression)
            continue

        aggregate = re.fullmatch(
            r"(COUNT|MIN|MAX|SUM)\(([A-Za-z_][A-Za-z0-9_]*)\)",
            field.expression.strip(),
            re.IGNORECASE,
        )
        if aggregate is None:
            raise ValueError(
                f"Unsupported Aggregator expression '{field.expression}' "
                f"on field '{field.name}'"
            )
        function, argument = aggregate.groups()
        projections.append(
            f"{function.upper()}({_sql_name(argument)}) AS {_sql_name(field.name)}"
        )

    upstream = _sql_name(next(iter(upstream_names)))
    return (
        "SELECT\n    "
        + ",\n    ".join(projections)
        + f"\nFROM {upstream}\nGROUP BY "
        + ", ".join(group_by)
    )


def _render_joiner(
    ancestry: TargetAncestry,
    instance_name: str,
    transformation: Transformation,
) -> str:
    if transformation.table_attributes.get("Join Type") != "Master Outer Join":
        raise ValueError("Only Master Outer Join is supported")
    if transformation.table_attributes.get("Sorted Input") != "NO":
        raise ValueError("Only unsorted Joiner input is supported")

    fields = {field.name: field for field in transformation.fields}
    incoming = _incoming(ancestry, instance_name)
    incoming_by_port = {connector.to_field: connector for connector in incoming}
    role_by_upstream: dict[str, str] = {}
    upstream_by_role: dict[str, str] = {}
    for connector in incoming:
        role = (
            "master"
            if "MASTER" in fields[connector.to_field].port_type.split("/")
            else "detail"
        )
        previous_role = role_by_upstream.setdefault(connector.from_instance, role)
        if previous_role != role:
            raise ValueError(
                f"Joiner upstream '{connector.from_instance}' mixes port roles"
            )
        previous_upstream = upstream_by_role.setdefault(role, connector.from_instance)
        if previous_upstream != connector.from_instance:
            raise ValueError(f"Joiner has multiple {role} upstream instances")

    if set(upstream_by_role) != {"master", "detail"}:
        raise ValueError("Joiner requires one master and one detail upstream instance")

    condition = transformation.table_attributes.get("Join Condition", "")
    equality = re.fullmatch(
        r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*",
        condition,
    )
    if equality is None:
        raise ValueError("Only a single equality Join Condition is supported")

    condition_parts: dict[str, str] = {}
    for port_name in equality.groups():
        connector = incoming_by_port[port_name]
        role = role_by_upstream[connector.from_instance]
        condition_parts[role] = f"{role}.{_sql_name(connector.from_field)}"

    downstream_fields = _downstream_fields(ancestry, instance_name)
    projections = []
    for field in transformation.fields:
        if field.name not in downstream_fields:
            continue
        connector = incoming_by_port[field.name]
        role = role_by_upstream[connector.from_instance]
        projections.append(
            f"{role}.{_sql_name(connector.from_field)} AS {_sql_name(field.name)}"
        )

    detail = _sql_name(upstream_by_role["detail"])
    master = _sql_name(upstream_by_role["master"])
    return (
        "SELECT\n    "
        + ",\n    ".join(projections)
        + f"\nFROM {detail} AS detail"
        + f"\nLEFT JOIN {master} AS master"
        + f"\n    ON {condition_parts['master']} = {condition_parts['detail']}"
    )


def _split_arguments(arguments: str) -> tuple[str, ...]:
    parts: list[str] = []
    start = 0
    depth = 0
    quoted = False
    index = 0
    while index < len(arguments):
        character = arguments[index]
        if character == "'":
            if quoted and index + 1 < len(arguments) and arguments[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
        elif not quoted:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("Unbalanced expression parentheses")
            elif character == "," and depth == 0:
                parts.append(arguments[start:index].strip())
                start = index + 1
        index += 1

    if quoted or depth != 0:
        raise ValueError("Unbalanced expression quotes or parentheses")
    parts.append(arguments[start:].strip())
    return tuple(parts)


def _top_level_greater_than(expression: str) -> int | None:
    depth = 0
    quoted = False
    index = 0
    while index < len(expression):
        character = expression[index]
        if character == "'":
            if quoted and index + 1 < len(expression) and expression[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
        elif not quoted:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            elif character == ">" and depth == 0:
                return index
        index += 1
    return None


def _translate_expression(expression: str) -> str:
    expression = expression.strip()
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
        return f"input.{_sql_name(expression)}"
    if re.fullmatch(r"-?\d+(?:\.\d+)?", expression):
        return expression
    if re.fullmatch(r"'(?:''|[^'])*'", expression):
        return expression

    greater_than = _top_level_greater_than(expression)
    if greater_than is not None:
        left = _translate_expression(expression[:greater_than])
        right = _translate_expression(expression[greater_than + 1 :])
        return f"{left} > {right}"

    function = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", expression, re.DOTALL
    )
    if function is None:
        raise ValueError(f"Unsupported expression '{expression}'")
    function_name, raw_arguments = function.groups()
    arguments = _split_arguments(raw_arguments)
    if function_name.upper() == "ISNULL" and len(arguments) == 1:
        return f"({_translate_expression(arguments[0])} IS NULL)"
    if function_name.upper() == "IIF" and len(arguments) == 3:
        condition, true_value, false_value = (
            _translate_expression(argument) for argument in arguments
        )
        return f"CASE WHEN {condition} THEN {true_value} ELSE {false_value} END"
    raise ValueError(f"Unsupported expression function '{function_name}'")


def _render_expression(
    ancestry: TargetAncestry,
    instance_name: str,
    transformation: Transformation,
) -> str:
    for field in transformation.fields:
        if "VARIABLE" in field.port_type.upper():
            raise ValueError(
                f"field '{field.name}' has unsupported stateful port type "
                f"'{field.port_type}'"
            )

    upstream_names = {
        connector.from_instance for connector in _incoming(ancestry, instance_name)
    }
    if len(upstream_names) != 1:
        raise ValueError(
            f"Expression '{instance_name}' requires exactly one upstream instance"
        )

    downstream_fields = _downstream_fields(ancestry, instance_name)
    projections = [
        f"{_translate_expression(field.expression)} AS {_sql_name(field.name)}"
        for field in transformation.fields
        if field.name in downstream_fields
    ]
    upstream = _sql_name(next(iter(upstream_names)))
    return (
        "SELECT\n    "
        + ",\n    ".join(projections)
        + f"\nFROM {upstream} AS input"
    )


def render_transformation(
    document: PowerCenterDocument,
    ancestry: TargetAncestry,
    instance_name: str,
) -> str:
    transformation = _transformation(document, ancestry, instance_name)
    try:
        if transformation.transformation_type == "Source Qualifier":
            return _render_source_qualifier(
                document, ancestry, instance_name, transformation
            )
        if transformation.transformation_type == "Aggregator":
            return _render_aggregator(ancestry, instance_name, transformation)
        if transformation.transformation_type == "Joiner":
            return _render_joiner(ancestry, instance_name, transformation)
        if transformation.transformation_type == "Expression":
            return _render_expression(ancestry, instance_name, transformation)
    except RenderingError:
        raise
    except ValueError as error:
        raise RenderingError(
            f"Mapping '{ancestry.mapping_name}', target '{ancestry.target_name}', "
            f"instance '{instance_name}' has unsupported "
            f"{transformation.transformation_type} configuration: {error}"
        ) from error
    raise RenderingError(
        f"Mapping '{ancestry.mapping_name}', target '{ancestry.target_name}', "
        f"instance '{instance_name}' has unsupported transformation type "
        f"'{transformation.transformation_type}'"
    )
