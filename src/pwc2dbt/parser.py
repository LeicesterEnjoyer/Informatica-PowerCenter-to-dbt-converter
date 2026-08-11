from pathlib import Path
from typing import Iterable, TypeVar
from xml.etree import ElementTree

from .model import (
    Connector,
    DefinitionField,
    Instance,
    PowerCenterDocument,
    PowerCenterMapping,
    SourceDefinition,
    TargetDefinition,
    TransformField,
    TransformGroup,
    Transformation,
)


Value = TypeVar("Value")


def _attributes(element: ElementTree.Element) -> dict[str, str]:
    return dict(element.attrib)


def _index(values: Iterable[Value]) -> dict[str, Value]:
    return {getattr(value, "name"): value for value in values}


def _definition_field(element: ElementTree.Element) -> DefinitionField:
    return DefinitionField(
        name=element.attrib["NAME"],
        datatype=element.attrib.get("DATATYPE", ""),
        attributes=_attributes(element),
    )


def _source(element: ElementTree.Element) -> SourceDefinition:
    return SourceDefinition(
        name=element.attrib["NAME"],
        owner_name=element.attrib.get("OWNERNAME", ""),
        database_type=element.attrib.get("DATABASETYPE", ""),
        fields=tuple(_definition_field(field) for field in element.findall("SOURCEFIELD")),
        attributes=_attributes(element),
    )


def _target(element: ElementTree.Element) -> TargetDefinition:
    return TargetDefinition(
        name=element.attrib["NAME"],
        database_type=element.attrib.get("DATABASETYPE", ""),
        fields=tuple(_definition_field(field) for field in element.findall("TARGETFIELD")),
        attributes=_attributes(element),
    )


def _transform_field(element: ElementTree.Element) -> TransformField:
    return TransformField(
        name=element.attrib["NAME"],
        datatype=element.attrib.get("DATATYPE", ""),
        port_type=element.attrib.get("PORTTYPE", ""),
        expression=element.attrib.get("EXPRESSION", ""),
        expression_type=element.attrib.get("EXPRESSIONTYPE", ""),
        group=element.attrib.get("GROUP", ""),
        attributes=_attributes(element),
    )


def _transform_group(element: ElementTree.Element) -> TransformGroup:
    return TransformGroup(
        name=element.attrib["NAME"],
        expression=element.attrib.get("EXPRESSION", ""),
        attributes=_attributes(element),
    )


def _transformation(element: ElementTree.Element) -> Transformation:
    table_attributes = {
        attribute.attrib["NAME"]: attribute.attrib.get("VALUE", "")
        for attribute in element.findall("TABLEATTRIBUTE")
    }
    return Transformation(
        name=element.attrib["NAME"],
        transformation_type=element.attrib.get("TYPE", ""),
        fields=tuple(
            _transform_field(field) for field in element.findall("TRANSFORMFIELD")
        ),
        groups=tuple(_transform_group(group) for group in element.findall("GROUP")),
        table_attributes=table_attributes,
        attributes=_attributes(element),
    )


def _instance(element: ElementTree.Element) -> Instance:
    return Instance(
        name=element.attrib["NAME"],
        transformation_name=element.attrib.get("TRANSFORMATION_NAME", ""),
        transformation_type=element.attrib.get("TRANSFORMATION_TYPE", ""),
        instance_type=element.attrib.get("TYPE", ""),
        attributes=_attributes(element),
    )


def _connector(element: ElementTree.Element) -> Connector:
    return Connector(
        from_instance=element.attrib["FROMINSTANCE"],
        from_field=element.attrib["FROMFIELD"],
        from_instance_type=element.attrib.get("FROMINSTANCETYPE", ""),
        to_instance=element.attrib["TOINSTANCE"],
        to_field=element.attrib["TOFIELD"],
        to_instance_type=element.attrib.get("TOINSTANCETYPE", ""),
        attributes=_attributes(element),
    )


def _mapping(element: ElementTree.Element) -> PowerCenterMapping:
    return PowerCenterMapping(
        name=element.attrib["NAME"],
        transformations=_index(
            _transformation(transformation)
            for transformation in element.findall("TRANSFORMATION")
        ),
        instances=_index(_instance(instance) for instance in element.findall("INSTANCE")),
        connectors=tuple(
            _connector(connector) for connector in element.findall("CONNECTOR")
        ),
        attributes=_attributes(element),
    )


def parse_powercenter(path: str | Path) -> PowerCenterDocument:
    root = ElementTree.parse(path).getroot()
    folders = root.findall("./REPOSITORY/FOLDER")
    return PowerCenterDocument(
        sources=_index(_source(source) for folder in folders for source in folder.findall("SOURCE")),
        targets=_index(_target(target) for folder in folders for target in folder.findall("TARGET")),
        mappings=_index(
            _mapping(mapping) for folder in folders for mapping in folder.findall("MAPPING")
        ),
    )
