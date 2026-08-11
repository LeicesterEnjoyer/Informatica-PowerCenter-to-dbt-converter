from pathlib import Path
from pwc2dbt.parser import parse_powercenter

SYNTHETIC_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<POWERMART>
  <REPOSITORY NAME="TEST_REPOSITORY">
    <FOLDER NAME="TEST_FOLDER">
      <SOURCE NAME="RAW_CUSTOMERS" OWNERNAME="RAW" DATABASETYPE="Oracle">
        <SOURCEFIELD NAME="ID" DATATYPE="varchar2" FIELDNUMBER="1"
                     PRECISION="100" SCALE="0" NULLABLE="NOTNULL" />
      </SOURCE>
      <TARGET NAME="CUSTOMERS" DATABASETYPE="Oracle">
        <TARGETFIELD NAME="CUSTOMER_ID" DATATYPE="varchar2" FIELDNUMBER="1"
                     PRECISION="100" SCALE="0" NULLABLE="NULL" />
      </TARGET>
      <MAPPING NAME="m_customers" ISVALID="YES">
        <TRANSFORMATION NAME="SQ_RAW_CUSTOMERS" TYPE="Source Qualifier">
          <TRANSFORMFIELD NAME="ID" DATATYPE="string"
                          PORTTYPE="INPUT/OUTPUT" EXPRESSION=""
                          EXPRESSIONTYPE="GENERAL" />
          <GROUP NAME="INPUT" TYPE="INPUT" EXPRESSION="ID IS NOT NULL" />
          <TABLEATTRIBUTE NAME="Select Distinct" VALUE="NO" />
        </TRANSFORMATION>
        <INSTANCE NAME="RAW_CUSTOMERS"
                  TRANSFORMATION_NAME="RAW_CUSTOMERS"
                  TRANSFORMATION_TYPE="Source Definition" TYPE="SOURCE" />
        <INSTANCE NAME="SQ_RAW_CUSTOMERS"
                  TRANSFORMATION_NAME="SQ_RAW_CUSTOMERS"
                  TRANSFORMATION_TYPE="Source Qualifier"
                  TYPE="TRANSFORMATION" />
        <INSTANCE NAME="CUSTOMERS" TRANSFORMATION_NAME="CUSTOMERS"
                  TRANSFORMATION_TYPE="Target Definition" TYPE="TARGET" />
        <CONNECTOR FROMINSTANCE="RAW_CUSTOMERS" FROMFIELD="ID"
                   FROMINSTANCETYPE="Source Definition"
                   TOINSTANCE="SQ_RAW_CUSTOMERS" TOFIELD="ID"
                   TOINSTANCETYPE="Source Qualifier" />
        <CONNECTOR FROMINSTANCE="SQ_RAW_CUSTOMERS" FROMFIELD="ID"
                   FROMINSTANCETYPE="Source Qualifier"
                   TOINSTANCE="CUSTOMERS" TOFIELD="CUSTOMER_ID"
                   TOINSTANCETYPE="Target Definition" />
      </MAPPING>
    </FOLDER>
  </REPOSITORY>
</POWERMART>
"""


def test_parses_required_powercenter_elements(tmp_path: Path) -> None:
    xml_path = tmp_path / "mapping.xml"
    xml_path.write_text(SYNTHETIC_XML, encoding="utf-8")

    document = parse_powercenter(xml_path)

    source = document.sources["RAW_CUSTOMERS"]
    assert source.owner_name == "RAW"
    assert source.database_type == "Oracle"
    assert [field.name for field in source.fields] == ["ID"]
    assert source.fields[0].datatype == "varchar2"
    assert source.fields[0].attributes["PRECISION"] == "100"

    target = document.targets["CUSTOMERS"]
    assert target.database_type == "Oracle"
    assert [field.name for field in target.fields] == ["CUSTOMER_ID"]

    mapping = document.mappings["m_customers"]
    assert mapping.attributes["ISVALID"] == "YES"

    transformation = mapping.transformations["SQ_RAW_CUSTOMERS"]
    assert transformation.transformation_type == "Source Qualifier"
    assert transformation.fields[0].name == "ID"
    assert transformation.fields[0].port_type == "INPUT/OUTPUT"
    assert transformation.fields[0].expression_type == "GENERAL"
    assert transformation.groups[0].name == "INPUT"
    assert transformation.groups[0].expression == "ID IS NOT NULL"
    assert transformation.table_attributes["Select Distinct"] == "NO"

    source_instance = mapping.instances["RAW_CUSTOMERS"]
    assert source_instance.transformation_name == "RAW_CUSTOMERS"
    assert source_instance.transformation_type == "Source Definition"
    assert source_instance.instance_type == "SOURCE"

    target_instance = mapping.instances["CUSTOMERS"]
    assert target_instance.transformation_name == "CUSTOMERS"
    assert target_instance.transformation_type == "Target Definition"
    assert target_instance.instance_type == "TARGET"

    assert len(mapping.connectors) == 2
    first_connector = mapping.connectors[0]
    assert first_connector.from_instance == "RAW_CUSTOMERS"
    assert first_connector.from_field == "ID"
    assert first_connector.to_instance == "SQ_RAW_CUSTOMERS"
    assert first_connector.to_field == "ID"


def test_finds_core_customers_in_supplied_xml() -> None:
    xml_path = (
        Path(__file__).parents[1] / "data" / "FLOWLINE_DEMO_JAFFLESHOP.xml"
    )

    document = parse_powercenter(xml_path)

    assert "m_FL_JS_MARTS_CORE" in document.mappings
    assert "CUSTOMERS" in document.targets
    assert "CUSTOMERS" in document.mappings["m_FL_JS_MARTS_CORE"].instances
