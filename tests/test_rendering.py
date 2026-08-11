from dataclasses import replace
from pathlib import Path

import pytest

from pwc2dbt.graph import build_target_ancestry
from pwc2dbt.parser import parse_powercenter
from pwc2dbt.rendering import RenderingError, render_transformation


def _core_customers():
    xml_path = (
        Path(__file__).parents[1] / "data" / "FLOWLINE_DEMO_JAFFLESHOP.xml"
    )
    document = parse_powercenter(xml_path)
    ancestry = build_target_ancestry(
        document, "m_FL_JS_MARTS_CORE", "CUSTOMERS"
    )
    return document, ancestry


def _replace_transformation(document, ancestry, transformation):
    mapping = document.mappings[ancestry.mapping_name]

    transformations = dict(mapping.transformations)
    transformations[transformation.name] = transformation

    mappings = dict(document.mappings)
    mappings[mapping.name] = replace(
        mapping,
        transformations=transformations,
    )

    return replace(document, mappings=mappings)


def test_renders_source_qualifier_projection_from_resolved_ref() -> None:
    document, ancestry = _core_customers()

    sql = render_transformation(document, ancestry, "SQ_STG_ORDERS2")

    assert sql.startswith("SELECT\n")
    assert "FROM {{ ref('stg_orders') }}" in sql
    for field in (
        "order_id",
        "customer_id",
        "ordered_at_day",
        "subtotal",
        "tax_paid",
        "order_total",
    ):
        assert field in sql
    assert "location_id" not in sql
    assert "subtotal_cents" not in sql


def test_renders_observed_aggregator_structure() -> None:
    document, ancestry = _core_customers()

    sql = render_transformation(document, ancestry, "AGG_ORDERS_BY_CUSTOMER")

    assert sql.startswith("SELECT\n")
    assert "FROM sq_stg_orders2" in sql
    assert "GROUP BY customer_id" in sql
    assert "COUNT(order_id) AS lifetime_orders" in sql
    assert "MIN(ordered_at_day) AS first_order_date" in sql
    assert "MAX(ordered_at_day) AS last_order_date" in sql
    assert "SUM(order_total) AS lifetime_spend" in sql
    assert "SUM(subtotal) AS lifetime_spend_pretax" in sql
    assert "SUM(tax_paid) AS lifetime_tax_paid" in sql


def test_renders_master_outer_join_with_detail_on_left() -> None:
    document, ancestry = _core_customers()

    sql = render_transformation(document, ancestry, "JNR_CUSTOMERS_ORDERS")

    assert sql.startswith("SELECT\n")
    assert "FROM agg_orders_by_customer AS detail" in sql
    assert "LEFT JOIN sq_stg_customers AS master" in sql
    assert "ON master.customer_id = detail.customer_id" in sql
    assert "master.customer_id AS customer_id" in sql
    assert "detail.lifetime_orders AS lifetime_orders" in sql
    assert "detail.customer_id AS customer_id," not in sql
    assert "COALESCE" not in sql


def test_renders_observed_stateless_expressions() -> None:
    document, ancestry = _core_customers()

    sql = render_transformation(document, ancestry, "EXP_CUSTOMER_METRICS")

    assert sql.startswith("SELECT\n")
    assert "FROM jnr_customers_orders AS input" in sql
    assert "input.customer_id AS customer_id" in sql
    assert (
        "CASE WHEN (input.lifetime_orders IS NULL) THEN 0 "
        "ELSE input.lifetime_orders END AS lifetime_orders_cl"
    ) in sql
    assert (
        "CASE WHEN CASE WHEN (input.lifetime_orders IS NULL) THEN 0 "
        "ELSE input.lifetime_orders END > 1 THEN 'returning' ELSE 'new' END "
        "AS customer_type"
    ) in sql


def test_rejects_reachable_unsupported_transformation_contextually() -> None:
    document, ancestry = _core_customers()
    mapping = document.mappings[ancestry.mapping_name]
    expression = mapping.transformations["EXP_CUSTOMER_METRICS"]
    document = _replace_transformation(
        document,
        ancestry,
        replace(
            expression,
            transformation_type="Router",
        ),
    )

    with pytest.raises(RenderingError) as error:
        render_transformation(document, ancestry, "EXP_CUSTOMER_METRICS")

    message = str(error.value)
    assert "m_FL_JS_MARTS_CORE" in message
    assert "CUSTOMERS" in message
    assert "EXP_CUSTOMER_METRICS" in message
    assert "Router" in message


def test_rejects_reachable_unsupported_configuration_contextually() -> None:
    document, ancestry = _core_customers()
    mapping = document.mappings[ancestry.mapping_name]
    joiner = mapping.transformations["JNR_CUSTOMERS_ORDERS"]
    table_attributes = dict(joiner.table_attributes)
    table_attributes["Join Type"] = "Normal Join"
    document = _replace_transformation(
        document,
        ancestry,
        replace(
            joiner, table_attributes=table_attributes
        )
    )

    with pytest.raises(RenderingError) as error:
        render_transformation(document, ancestry, "JNR_CUSTOMERS_ORDERS")

    message = str(error.value)
    assert "m_FL_JS_MARTS_CORE" in message
    assert "CUSTOMERS" in message
    assert "JNR_CUSTOMERS_ORDERS" in message
    assert "Joiner" in message
    assert "Master Outer Join" in message


def test_rejects_stateful_expression_ports() -> None:
    document, ancestry = _core_customers()
    mapping = document.mappings[ancestry.mapping_name]
    expression = mapping.transformations["EXP_CUSTOMER_METRICS"]
    fields = tuple(
        replace(field, port_type="LOCAL VARIABLE")
        if field.name == "LIFETIME_ORDERS"
        else field
        for field in expression.fields
    )
    document = _replace_transformation(
        document,
        ancestry,
        replace(expression, fields=fields)
    )

    with pytest.raises(RenderingError) as error:
        render_transformation(document, ancestry, "EXP_CUSTOMER_METRICS")

    message = str(error.value)
    assert "EXP_CUSTOMER_METRICS" in message
    assert "LOCAL VARIABLE" in message
    assert "LIFETIME_ORDERS" in message


def test_rejects_source_qualifier_filter_instead_of_dropping_it() -> None:
    document, ancestry = _core_customers()
    mapping = document.mappings[ancestry.mapping_name]
    qualifier = mapping.transformations["SQ_STG_ORDERS2"]
    table_attributes = dict(qualifier.table_attributes)
    table_attributes["Source Filter"] = "ORDER_ID IS NOT NULL"
    document = _replace_transformation(
        document,
        ancestry,
        replace(
            qualifier, table_attributes=table_attributes
        )
    )

    with pytest.raises(RenderingError) as error:
        render_transformation(document, ancestry, "SQ_STG_ORDERS2")

    message = str(error.value)
    assert "SQ_STG_ORDERS2" in message
    assert "Source Filter" in message
    assert "ORDER_ID IS NOT NULL" in message


def test_rejects_sorted_aggregator_configuration() -> None:
    document, ancestry = _core_customers()
    mapping = document.mappings[ancestry.mapping_name]
    aggregator = mapping.transformations["AGG_ORDERS_BY_CUSTOMER"]
    table_attributes = dict(aggregator.table_attributes)
    table_attributes["Sorted Input"] = "YES"
    document = _replace_transformation(
        document,
        ancestry,
        replace(
            aggregator, table_attributes=table_attributes
        )
    )

    with pytest.raises(RenderingError) as error:
        render_transformation(document, ancestry, "AGG_ORDERS_BY_CUSTOMER")

    message = str(error.value)
    assert "AGG_ORDERS_BY_CUSTOMER" in message
    assert "Sorted Input" in message
    assert "NO" in message
