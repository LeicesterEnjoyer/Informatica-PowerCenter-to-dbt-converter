import pytest
from pathlib import Path

from pwc2dbt.graph import (
    GraphSelectionError,
    SourceResolutionError,
    build_target_ancestry,
    resolve_source_refs,
)
from pwc2dbt.parser import parse_powercenter

SYNTHETIC_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<POWERMART>
  <REPOSITORY NAME="TEST_REPOSITORY">
    <FOLDER NAME="TEST_FOLDER">
      <SOURCE NAME="STG_ORDERS" DATABASETYPE="Oracle">
        <SOURCEFIELD NAME="ORDER_ID" DATATYPE="varchar2" />
      </SOURCE>
      <SOURCE NAME="RAW_UNUSED" DATABASETYPE="Oracle">
        <SOURCEFIELD NAME="ID" DATATYPE="varchar2" />
      </SOURCE>
      <TARGET NAME="STG_ORDERS" DATABASETYPE="Oracle">
        <TARGETFIELD NAME="ORDER_ID" DATATYPE="varchar2" />
      </TARGET>
      <TARGET NAME="CUSTOMERS" DATABASETYPE="Oracle">
        <TARGETFIELD NAME="ORDER_ID" DATATYPE="varchar2" />
      </TARGET>
      <TARGET NAME="UNRELATED_TARGET" DATABASETYPE="Oracle">
        <TARGETFIELD NAME="ID" DATATYPE="varchar2" />
      </TARGET>
      <MAPPING NAME="m_selected">
        <TRANSFORMATION NAME="SQ_ORDERS" TYPE="Source Qualifier" />
        <TRANSFORMATION NAME="RTR_UNUSED" TYPE="Router" />
        <INSTANCE NAME="ORDER_INPUT_2026"
                  TRANSFORMATION_NAME="STG_ORDERS"
                  TRANSFORMATION_TYPE="Source Definition" TYPE="SOURCE" />
        <INSTANCE NAME="SQ_ORDERS" TRANSFORMATION_NAME="SQ_ORDERS"
                  TRANSFORMATION_TYPE="Source Qualifier"
                  TYPE="TRANSFORMATION" />
        <INSTANCE NAME="CUSTOMERS" TRANSFORMATION_NAME="CUSTOMERS"
                  TRANSFORMATION_TYPE="Target Definition" TYPE="TARGET" />
        <INSTANCE NAME="RAW_UNUSED" TRANSFORMATION_NAME="RAW_UNUSED"
                  TRANSFORMATION_TYPE="Source Definition" TYPE="SOURCE" />
        <INSTANCE NAME="RTR_UNUSED" TRANSFORMATION_NAME="RTR_UNUSED"
                  TRANSFORMATION_TYPE="Router" TYPE="TRANSFORMATION" />
        <INSTANCE NAME="UNRELATED_TARGET"
                  TRANSFORMATION_NAME="UNRELATED_TARGET"
                  TRANSFORMATION_TYPE="Target Definition" TYPE="TARGET" />
        <CONNECTOR FROMINSTANCE="ORDER_INPUT_2026" FROMFIELD="ORDER_ID"
                   FROMINSTANCETYPE="Source Definition"
                   TOINSTANCE="SQ_ORDERS" TOFIELD="ORDER_ID"
                   TOINSTANCETYPE="Source Qualifier" />
        <CONNECTOR FROMINSTANCE="SQ_ORDERS" FROMFIELD="ORDER_ID"
                   FROMINSTANCETYPE="Source Qualifier"
                   TOINSTANCE="CUSTOMERS" TOFIELD="ORDER_ID"
                   TOINSTANCETYPE="Target Definition" />
        <CONNECTOR FROMINSTANCE="RAW_UNUSED" FROMFIELD="ID"
                   FROMINSTANCETYPE="Source Definition"
                   TOINSTANCE="RTR_UNUSED" TOFIELD="ID"
                   TOINSTANCETYPE="Router" />
        <CONNECTOR FROMINSTANCE="RTR_UNUSED" FROMFIELD="ID"
                   FROMINSTANCETYPE="Router"
                   TOINSTANCE="UNRELATED_TARGET" TOFIELD="ID"
                   TOINSTANCETYPE="Target Definition" />
      </MAPPING>
    </FOLDER>
  </REPOSITORY>
</POWERMART>
"""


def _parse_xml(tmp_path: Path, xml: str = SYNTHETIC_XML):
    xml_path = tmp_path / "mapping.xml"
    xml_path.write_text(xml, encoding="utf-8")
    return parse_powercenter(xml_path)


def test_builds_only_selected_target_ancestry(tmp_path: Path) -> None:
    document = _parse_xml(tmp_path)

    ancestry = build_target_ancestry(document, "m_selected", "CUSTOMERS")

    assert set(ancestry.instances) == {
        "ORDER_INPUT_2026",
        "SQ_ORDERS",
        "CUSTOMERS",
    }
    assert {(edge.from_instance, edge.to_instance) for edge in ancestry.connectors} == {
        ("ORDER_INPUT_2026", "SQ_ORDERS"),
        ("SQ_ORDERS", "CUSTOMERS"),
    }
    assert "RTR_UNUSED" not in ancestry.instances
    assert "UNRELATED_TARGET" not in ancestry.instances


def test_finds_exact_core_customers_ancestry_in_supplied_xml() -> None:
    xml_path = (
        Path(__file__).parents[1] / "data" / "FLOWLINE_DEMO_JAFFLESHOP.xml"
    )
    document = parse_powercenter(xml_path)

    ancestry = build_target_ancestry(
        document, "m_FL_JS_MARTS_CORE", "CUSTOMERS"
    )

    assert set(ancestry.instances) == {
        "STG_ORDERS2",
        "SQ_STG_ORDERS2",
        "AGG_ORDERS_BY_CUSTOMER",
        "STG_CUSTOMERS",
        "SQ_STG_CUSTOMERS",
        "JNR_CUSTOMERS_ORDERS",
        "EXP_CUSTOMER_METRICS",
        "CUSTOMERS",
    }
    assert sum(
        instance.transformation_type == "Source Definition"
        for instance in ancestry.instances.values()
    ) == 2
    assert sum(
        instance.instance_type == "TRANSFORMATION"
        for instance in ancestry.instances.values()
    ) == 5


def test_resolves_refs_from_source_definition_metadata(tmp_path: Path) -> None:
    document = _parse_xml(tmp_path)
    ancestry = build_target_ancestry(document, "m_selected", "CUSTOMERS")

    refs = resolve_source_refs(document, ancestry)

    assert ancestry.instances["ORDER_INPUT_2026"].transformation_name == "STG_ORDERS"
    assert refs == {"ORDER_INPUT_2026": "{{ ref('stg_orders') }}"}


def test_resolves_supplied_core_source_refs() -> None:
    xml_path = (
        Path(__file__).parents[1] / "data" / "FLOWLINE_DEMO_JAFFLESHOP.xml"
    )
    document = parse_powercenter(xml_path)
    ancestry = build_target_ancestry(
        document, "m_FL_JS_MARTS_CORE", "CUSTOMERS"
    )

    refs = resolve_source_refs(document, ancestry)

    assert refs["STG_ORDERS2"] == "{{ ref('stg_orders') }}"
    assert refs["STG_CUSTOMERS"] == "{{ ref('stg_customers') }}"


@pytest.mark.parametrize(
    ("mapping_name", "target_name", "expected_message"),
    [
        ("missing_mapping", "CUSTOMERS", "Unknown mapping 'missing_mapping'"),
        ("m_selected", "missing_target", "Unknown target 'missing_target'"),
    ],
)
def test_reports_unknown_mapping_or_target(
    tmp_path: Path,
    mapping_name: str,
    target_name: str,
    expected_message: str,
) -> None:
    document = _parse_xml(tmp_path)

    with pytest.raises(GraphSelectionError, match=expected_message):
        build_target_ancestry(document, mapping_name, target_name)


def test_rejects_raw_source_resolution_descriptively(tmp_path: Path) -> None:
    document = _parse_xml(tmp_path)
    ancestry = build_target_ancestry(document, "m_selected", "UNRELATED_TARGET")

    with pytest.raises(SourceResolutionError) as error:
        resolve_source_refs(document, ancestry)

    message = str(error.value)
    assert "RAW_UNUSED" in message
    assert "matching target definition" in message
    assert "source() is outside the supported scope" in message
