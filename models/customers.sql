WITH
sq_stg_orders2 AS (
    SELECT
        order_id,
        customer_id,
        ordered_at_day,
        subtotal,
        tax_paid,
        order_total
    FROM {{ ref('stg_orders') }}
),
sq_stg_customers AS (
    SELECT
        customer_id,
        customer_name
    FROM {{ ref('stg_customers') }}
),
agg_orders_by_customer AS (
    SELECT
        customer_id,
        COUNT(order_id) AS lifetime_orders,
        MIN(ordered_at_day) AS first_order_date,
        MAX(ordered_at_day) AS last_order_date,
        SUM(order_total) AS lifetime_spend,
        SUM(subtotal) AS lifetime_spend_pretax,
        SUM(tax_paid) AS lifetime_tax_paid
    FROM sq_stg_orders2
    GROUP BY customer_id
),
jnr_customers_orders AS (
    SELECT
        master.customer_id AS customer_id,
        master.customer_name AS customer_name,
        detail.lifetime_orders AS lifetime_orders,
        detail.first_order_date AS first_order_date,
        detail.last_order_date AS last_order_date,
        detail.lifetime_spend AS lifetime_spend,
        detail.lifetime_spend_pretax AS lifetime_spend_pretax,
        detail.lifetime_tax_paid AS lifetime_tax_paid
    FROM agg_orders_by_customer AS detail
    LEFT JOIN sq_stg_customers AS master
        ON master.customer_id = detail.customer_id
),
exp_customer_metrics AS (
    SELECT
        input.customer_id AS customer_id,
        input.customer_name AS customer_name,
        CASE WHEN (input.lifetime_orders IS NULL) THEN 0 ELSE input.lifetime_orders END AS lifetime_orders_cl,
        input.first_order_date AS first_order_date,
        input.last_order_date AS last_order_date,
        CASE WHEN (input.lifetime_spend IS NULL) THEN 0 ELSE input.lifetime_spend END AS lifetime_spend_cl,
        CASE WHEN (input.lifetime_spend_pretax IS NULL) THEN 0 ELSE input.lifetime_spend_pretax END AS lifetime_spend_pretax_cl,
        CASE WHEN (input.lifetime_tax_paid IS NULL) THEN 0 ELSE input.lifetime_tax_paid END AS lifetime_tax_paid_cl,
        CASE WHEN CASE WHEN (input.lifetime_orders IS NULL) THEN 0 ELSE input.lifetime_orders END > 1 THEN 'returning' ELSE 'new' END AS customer_type
    FROM jnr_customers_orders AS input
)
SELECT
    input.customer_id AS customer_id,
    input.customer_name AS customer_name,
    input.lifetime_orders_cl AS lifetime_orders,
    input.first_order_date AS first_order_date,
    input.last_order_date AS last_order_date,
    input.lifetime_spend_cl AS lifetime_spend,
    input.lifetime_spend_pretax_cl AS lifetime_spend_pretax,
    input.lifetime_tax_paid_cl AS lifetime_tax_paid,
    input.customer_type AS customer_type
FROM exp_customer_metrics AS input
