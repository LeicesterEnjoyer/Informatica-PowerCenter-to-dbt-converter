import re
from dataclasses import dataclass
from typing import Mapping

from .model import Connector, Instance, PowerCenterDocument


class GraphSelectionError(ValueError):
    """The requested mapping target cannot be selected or traversed."""


class SourceResolutionError(ValueError):
    """A reached source instance cannot be represented by a dbt ref."""


@dataclass(frozen=True)
class TargetAncestry:
    mapping_name: str
    target_name: str
    instances: Mapping[str, Instance]
    connectors: tuple[Connector, ...]


def build_target_ancestry(
    document: PowerCenterDocument,
    mapping_name: str,
    target_name: str,
) -> TargetAncestry:
    try:
        mapping = document.mappings[mapping_name]
    except KeyError as error:
        raise GraphSelectionError(f"Unknown mapping '{mapping_name}'") from error

    target = mapping.instances.get(target_name)
    if (
        target is None
        or target.instance_type != "TARGET"
        or target.transformation_type != "Target Definition"
    ):
        raise GraphSelectionError(
            f"Unknown target '{target_name}' in mapping '{mapping_name}'"
        )

    incoming: dict[str, list[tuple[int, Connector]]] = {}
    for index, connector in enumerate(mapping.connectors):
        incoming.setdefault(connector.to_instance, []).append((index, connector))

    reachable = {target_name}
    connector_indexes: set[int] = set()
    pending = [target_name]
    while pending:
        downstream_name = pending.pop()
        for index, connector in incoming.get(downstream_name, []):
            connector_indexes.add(index)
            upstream_name = connector.from_instance
            if upstream_name not in mapping.instances:
                raise GraphSelectionError(
                    f"Connector into target '{target_name}' in mapping "
                    f"'{mapping_name}' references unknown upstream instance "
                    f"'{upstream_name}'"
                )
            if upstream_name not in reachable:
                reachable.add(upstream_name)
                pending.append(upstream_name)

    return TargetAncestry(
        mapping_name=mapping_name,
        target_name=target_name,
        instances={
            name: instance
            for name, instance in mapping.instances.items()
            if name in reachable
        },
        connectors=tuple(
            connector
            for index, connector in enumerate(mapping.connectors)
            if index in connector_indexes
        ),
    )


def resolve_source_refs(
    document: PowerCenterDocument,
    ancestry: TargetAncestry,
) -> dict[str, str]:
    refs: dict[str, str] = {}
    for instance in ancestry.instances.values():
        if (
            instance.instance_type != "SOURCE"
            or instance.transformation_type != "Source Definition"
        ):
            continue

        definition_name = instance.transformation_name
        if definition_name not in document.sources:
            raise SourceResolutionError(
                f"Source instance '{instance.name}' in mapping "
                f"'{ancestry.mapping_name}' references unknown source definition "
                f"'{definition_name}'"
            )
        if definition_name not in document.targets:
            raise SourceResolutionError(
                f"Source instance '{instance.name}' resolves to source definition "
                f"'{definition_name}', which has no matching target definition; "
                "dbt source() is outside the supported scope"
            )

        resource_name = re.sub(r"[^0-9A-Za-z]+", "_", definition_name)
        resource_name = resource_name.strip("_").lower()

        if not resource_name:
            raise SourceResolutionError(
                f"Source definition '{definition_name}' cannot be normalized "
                "to a dbt resource name"
            )
        
        refs[instance.name] = f"{{{{ ref('{resource_name}') }}}}"

    return refs
