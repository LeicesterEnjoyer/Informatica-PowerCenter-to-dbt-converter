from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DefinitionField:
    name: str
    datatype: str
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    owner_name: str
    database_type: str
    fields: tuple[DefinitionField, ...]
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class TargetDefinition:
    name: str
    database_type: str
    fields: tuple[DefinitionField, ...]
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class TransformField:
    name: str
    datatype: str
    port_type: str
    expression: str
    expression_type: str
    group: str
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class TransformGroup:
    name: str
    expression: str
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class Transformation:
    name: str
    transformation_type: str
    fields: tuple[TransformField, ...]
    groups: tuple[TransformGroup, ...]
    table_attributes: Mapping[str, str]
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class Instance:
    name: str
    transformation_name: str
    transformation_type: str
    instance_type: str
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class Connector:
    from_instance: str
    from_field: str
    from_instance_type: str
    to_instance: str
    to_field: str
    to_instance_type: str
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class PowerCenterMapping:
    name: str
    transformations: Mapping[str, Transformation]
    instances: Mapping[str, Instance]
    connectors: tuple[Connector, ...]
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class PowerCenterDocument:
    sources: Mapping[str, SourceDefinition]
    targets: Mapping[str, TargetDefinition]
    mappings: Mapping[str, PowerCenterMapping]
