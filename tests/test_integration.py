from datetime import date
from pathlib import Path

import duckdb

from pwc2dbt.cli import main


TARGET_FIELDS = [
    "customer_id",
    "customer_name",
    "lifetime_orders",
    "first_order_date",
    "last_order_date",
    "lifetime_spend",
    "lifetime_spend_pretax",
    "lifetime_tax_paid",
    "customer_type",
]


def test_converts_core_customers_from_supplied_xml(tmp_path: Path) -> None:
    xml_path = (
        Path(__file__).parents[1] / "data" / "FLOWLINE_DEMO_JAFFLESHOP.xml"
    )
    output_path = tmp_path / "customers.sql"

    exit_code = main(
        [
            str(xml_path),
            "--mapping",
            "m_FL_JS_MARTS_CORE",
            "--target",
            "CUSTOMERS",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    sql = output_path.read_text(encoding="utf-8")
    assert sql.count("{{ ref('stg_orders') }}") == 1
    assert sql.count("{{ ref('stg_customers') }}") == 1
    assert not sql.rstrip().endswith(";")

    final_select = sql.rsplit("SELECT\n", maxsplit=1)[1]
    projection, _ = final_select.split("\nFROM ", maxsplit=1)
    projected_fields = [
        line.rstrip(",").rsplit(" AS ", maxsplit=1)[1]
        for line in projection.splitlines()
        if line.strip()
    ]
    assert projected_fields == TARGET_FIELDS

    compiled_sql = sql.replace("{{ ref('stg_orders') }}", "stg_orders").replace(
        "{{ ref('stg_customers') }}", "stg_customers"
    )
    connection = duckdb.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE stg_orders (
            order_id VARCHAR,
            customer_id VARCHAR,
            ordered_at_day DATE,
            subtotal DECIMAL(12, 2),
            tax_paid DECIMAL(12, 2),
            order_total DECIMAL(12, 2)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO stg_orders VALUES
            ('O1', 'C1', '2024-01-01', 10, 1, 11),
            ('O2', 'C1', '2024-01-03', 20, 2, 22),
            ('O3', 'C3', '2024-02-01', NULL, NULL, NULL)
        """
    )
    connection.execute(
        """
        CREATE TABLE stg_customers (
            customer_id VARCHAR,
            customer_name VARCHAR
        )
        """
    )
    connection.execute(
        """
        INSERT INTO stg_customers VALUES
            ('C1', 'Alice'),
            ('C2', 'Master Only')
        """
    )

    result = connection.execute(
        f"SELECT * FROM ({compiled_sql}) result ORDER BY customer_name NULLS LAST"
    )
    assert [column[0] for column in result.description] == TARGET_FIELDS
    assert result.fetchall() == [
        (
            "C1",
            "Alice",
            2,
            date(2024, 1, 1),
            date(2024, 1, 3),
            33,
            30,
            3,
            "returning",
        ),
        (
            None,
            None,
            1,
            date(2024, 2, 1),
            date(2024, 2, 1),
            0,
            0,
            0,
            "new",
        ),
    ]
