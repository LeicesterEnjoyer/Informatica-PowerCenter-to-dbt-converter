# PowerCenter XML to dbt Converter Specification

## 1. Purpose and scope

This document specifies a four-hour vertical slice of a converter from an
Informatica PowerCenter XML mapping export to a dbt SQL model. It distinguishes
source requirements, XML evidence, implementation decisions, assumptions,
exclusions, and acceptance criteria. Statements about the selected mapping are
derived from `data/FLOWLINE_DEMO_JAFFLESHOP.xml`; they are not inferred from the
Jaffle Shop domain.

The guaranteed and tested slice is target `CUSTOMERS` in mapping
`m_FL_JS_MARTS_CORE`. The parser and graph representation must remain generic,
and conversion must be selected by mapping and target rather than by
target-specific code. Another target may convert successfully when its entire
upstream ancestry uses the same supported configurations, but no other target
is guaranteed in this scope.

## 2. Requirements stated by the assignment

The following are requirements from `docs/ASSIGNMENT.md` and `AGENTS.md`, not
claims about the supplied XML:

- Read a PowerCenter XML mapping and derive the conversion from its structure;
  do not hard-code Jaffle Shop SQL.
- Produce a dbt model, which is a SQL `SELECT` statement in a `.sql` file.
- Provide a command-line way to run the converter.
- Include tests for supported conversion behavior.
- Prefer a descriptive error to SQL whose meaning is unknown or potentially
  incorrect.
- Explain assumptions, exclusions, and likely failure points in project
  documentation.
- Keep the work appropriate for approximately four hours; broad PowerCenter
  feature coverage is not required.
- Do not modify the supplied XML.

The Jaffle Shop DuckDB repository is a reference for dbt project conventions
and local DuckDB execution. It is not a semantic oracle for this XML: the
current reference project describes a smaller customers/orders/payments data
set, while the supplied XML contains different raw and mart definitions.

## 3. Facts directly observed in the supplied XML

### 3.1 Export inventory

- The export contains three mappings:
  `m_FL_JS_STAGING_FULL`, `m_FL_JS_MARTS_CORE`, and
  `m_FL_JS_MARTS_ENRICHED`.
- Across the folder there are 12 source definitions and 16 target definitions.
- `m_FL_JS_MARTS_CORE` contains 29 transformations, 46 instances, and 277
  connectors. These mapping-wide counts are inventory only; unrelated branches
  are not part of target-level validation.
- The `CUSTOMERS` target definition has exactly these nine fields, in target
  order:
  `CUSTOMER_ID`, `CUSTOMER_NAME`, `LIFETIME_ORDERS`, `FIRST_ORDER_DATE`,
  `LAST_ORDER_DATE`, `LIFETIME_SPEND`, `LIFETIME_SPEND_PRETAX`,
  `LIFETIME_TAX_PAID`, and `CUSTOMER_TYPE`.

### 3.2 Upstream ancestry of `m_FL_JS_MARTS_CORE.CUSTOMERS`

Walking `CONNECTOR` elements backward from `CUSTOMERS` reaches only the
following two source branches and their merge:

```text
STG_ORDERS2 (Source Definition instance)
  -> SQ_STG_ORDERS2 (Source Qualifier)
  -> AGG_ORDERS_BY_CUSTOMER (Aggregator)
                                      \
                                       -> JNR_CUSTOMERS_ORDERS (Joiner)
                                      /   -> EXP_CUSTOMER_METRICS (Expression)
STG_CUSTOMERS (Source Definition instance)       -> CUSTOMERS (Target)
  -> SQ_STG_CUSTOMERS (Source Qualifier)
```

No Router, Union, Sorter, Filter, custom transformation, or stateful variable
port is reachable from this target.

### 3.3 Source-definition metadata

- Source instance `STG_ORDERS2` has `TRANSFORMATION_NAME="STG_ORDERS"` and
  therefore refers to the source definition named `STG_ORDERS`.
- Source instance `STG_CUSTOMERS` has
  `TRANSFORMATION_NAME="STG_CUSTOMERS"` and refers to that source definition.
- Matching target definitions named `STG_ORDERS` and `STG_CUSTOMERS` also exist
  in the XML. Their presence justifies treating these relations as upstream dbt
  models for this slice.
- The numeric suffix in instance name `STG_ORDERS2` is instance identity, not
  the relation name. The XML already provides the relation identity through
  `TRANSFORMATION_NAME`.

### 3.4 Source Qualifiers

`SQ_STG_ORDERS2` and `SQ_STG_CUSTOMERS` have empty `Sql Query`,
`User Defined Join`, and `Source Filter` attributes. Both declare
`Select Distinct=NO` and zero sorted ports. Within the selected ancestry they
act as field projections from their respective source definitions. Only ports
connected to downstream transformations affect the generated model.

### 3.5 Aggregation

`AGG_ORDERS_BY_CUSTOMER` groups by `CUSTOMER_ID` and defines:

| Output port | XML expression |
| --- | --- |
| `LIFETIME_ORDERS` | `COUNT(ORDER_ID)` |
| `FIRST_ORDER_DATE` | `MIN(ORDERED_AT_DAY)` |
| `LAST_ORDER_DATE` | `MAX(ORDERED_AT_DAY)` |
| `LIFETIME_SPEND` | `SUM(ORDER_TOTAL)` |
| `LIFETIME_SPEND_PRETAX` | `SUM(SUBTOTAL)` |
| `LIFETIME_TAX_PAID` | `SUM(TAX_PAID)` |

Its `Sorted Input` attribute is `NO`; no Sorter is required by this ancestry.

### 3.6 Join

`JNR_CUSTOMERS_ORDERS` declares:

- join condition `CUSTOMER_ID = CUSTOMER_ID1`;
- join type `Master Outer Join`;
- `CUSTOMER_ID` and `CUSTOMER_NAME` as master ports, supplied by
  `SQ_STG_CUSTOMERS`;
- `CUSTOMER_ID1` and the aggregate metric ports as detail inputs, supplied by
  `AGG_ORDERS_BY_CUSTOMER`.

PowerCenter documentation states that a master outer join retains every detail
row and matching master rows, while discarding unmatched master rows. Therefore
this XML configuration preserves aggregated-order rows, not customer rows. An
equivalent SQL shape is the aggregated-orders/detail relation left-joined to
the customers/master relation. The converter must follow the declared port
roles and join type rather than infer a customer-preserving join from names or
Jaffle Shop expectations.

### 3.7 Stateless expressions and target projection

`EXP_CUSTOMER_METRICS` contains no local variable ports. It passes through
customer identifiers, names, and first/last order dates, and maps null aggregate
metrics to zero with expressions of this form:

```text
IIF(ISNULL(metric), 0, metric)
```

It defines `CUSTOMER_TYPE` as:

```text
IIF(IIF(ISNULL(LIFETIME_ORDERS), 0, LIFETIME_ORDERS) > 1,
    'returning',
    'new')
```

Connectors map the expression outputs to all nine `CUSTOMERS` target fields.

## 4. Proposed implementation decisions

These decisions define the intended implementation; they are not existing XML
behavior.

### 4.1 Command and selection contract

The CLI will accept an XML path, mapping name, target name, and output
location. It will produce one dbt `.sql` model for the selected target or exit
non-zero with a descriptive error. The guaranteed invocation selects
`m_FL_JS_MARTS_CORE` and `CUSTOMERS`, producing `customers.sql`.

Mapping and target names are runtime inputs. The parser, graph traversal, and
renderer must not contain branches keyed to those two names. The guarantee is
established by fixtures and integration tests, not by an allowlist.

### 4.2 Generic parsing and ancestry-local validation

- Parse source definitions, target definitions, mappings, transformations,
  instances, ports, transformation attributes, and connectors into explicit
  representations.
- Resolve a requested mapping and target, then walk incoming connectors from
  the target to construct only its upstream subgraph.
- Validate instance references, connector endpoints, port references, cycles,
  and transformation support only inside that subgraph.
- Do not validate or render independent mappings, unrelated target branches,
  sessions, or workflows as a prerequisite for converting the selected target.
- If the selected ancestry reaches an unsupported construct, report the
  mapping, target, instance, transformation type, and unsupported configuration
  where available.

This boundary means unsupported content elsewhere in the same XML must not
block conversion of `CUSTOMERS`.

### 4.3 Relation resolution

- Resolve a source instance to a source definition by its
  `TRANSFORMATION_NAME`; do not edit or strip suffixes from the instance name.
- Normalize the resolved source-definition name to lower snake case for a dbt
  resource name.
- Emit `ref()` only when a target definition with the resolved name exists in
  the XML. For this slice, the results are `{{ ref('stg_orders') }}` and
  `{{ ref('stg_customers') }}`.
- A missing or ambiguous source definition, or a resolved staging definition
  without the required matching target definition, is a descriptive error.

Raw source definitions and dbt `source()` declaration or resolution are
outside the initial vertical slice. If a selected ancestry reaches a raw
source that cannot be resolved through the supported `ref()` rule, conversion
must fail explicitly rather than emit a guessed table name or `source()` call.

### 4.4 Supported SQL rendering configurations

Rendering is capability-based. It supports only:

- a Source Qualifier with no SQL override, source filter, join override, or
  distinct behavior;
- an Aggregator whose connected outputs use direct group-by ports and the
  observed single-level `COUNT(column)`, `MIN(column)`, `MAX(column)`, or
  `SUM(column)` expressions;
- an equality Joiner with the observed unsorted `Master Outer Join`
  configuration and unambiguous master/detail ports;
- stateless Expression ports containing direct port references, string or
  numeric literals, comparison `>`, `ISNULL`, and nested `IIF` in the forms
  required by `EXP_CUSTOMER_METRICS`;
- final projection and aliasing according to connectors into the target fields.

The output will be a single DuckDB-compatible dbt `SELECT`, organized with
CTEs as needed. Expression translation will use SQL `coalesce` and `case`
constructs while preserving the observed result logic.

Support is determined from transformation type and configuration, not from
instance names. Other targets using only these configurations may therefore
succeed, but they are not acceptance-tested guarantees.

## 5. Assumptions requiring validation

These assumptions must not be presented as proven semantic equivalence until
validated by tests or manual execution:

- Matching source and target definition names represent an upstream dbt model
  suitable for `ref()`. This is supported structurally for the selected slice
  but the XML does not itself define dbt resources.
- DuckDB `COUNT`, `MIN`, `MAX`, and `SUM` over the test datatypes reproduce the
  selected PowerCenter aggregate results, including null handling.
- SQL `coalesce(metric, 0)` and `case` reproduce the selected `ISNULL` and
  `IIF` expressions for the fixture values and inferred result types.
- Identifier normalization to lower snake case is appropriate for the emitted
  dbt resource names.
- Source and target column datatypes need not be explicitly cast for the
  selected fixtures. The converter must not claim general Oracle-to-DuckDB
  datatype equivalence.

The unusual join direction is not an assumption: it follows from the XML
master-port markers and documented Master Outer Join behavior. Whether that
configuration reflects the mapping author's business intent remains unknown
and is outside the converter's responsibility.

## 6. Functionality intentionally excluded

The following are outside the four-hour scope:

- target-instance Pre SQL and Post SQL, including
  `TRUNCATE TABLE MART.CUSTOMERS`; these describe target execution and loading
  behavior rather than the SQL SELECT transformation;
- guaranteed conversion of any target other than
  `m_FL_JS_MARTS_CORE.CUSTOMERS`;
- raw source definitions, dbt source YAML generation, and dbt `source()`
  resolution;
- Router, Union, Sorter, Filter, Lookup, and general Custom transformations;
- stateful or local-variable expression ports, including sequence and
  previous-row logic;
- Joiner configurations other than the observed equality-based, unsorted
  Master Outer Join;
- arbitrary PowerCenter expression parsing or functions beyond the selected
  expression subset;
- Source Qualifier SQL overrides, filters, joins, distinct selection, or
  pre/post-SQL;
- incremental aggregation, sorted aggregation, transaction semantics, update
  strategy, target loading modes, and reject handling;
- sessions, workflows, scheduling, connection execution, mapping parameters,
  and workflow variables;
- automatic dbt project scaffolding, materialization configuration, schema
  tests, documentation generation, and orchestration;
- general Oracle-to-DuckDB datatype or function conversion;
- semantic comparison against the entire Jaffle Shop project.

Encountering an excluded feature in the selected ancestry is an error.
Encountering one only in an independent mapping or unrelated branch is not.

### 6.1 Stretch validation

The following validation cases are stretch goals and must not take priority
over the working end-to-end conversion:

- cycle detection;
- ambiguous duplicate definitions;
- malformed content in unrelated mappings;
- exhaustive validation of every connector and port error.

## 7. Measurable acceptance criteria

The initial vertical slice is accepted only when all of the following hold:

1. The CLI selects a mapping and target from an XML path and writes one model
   without modifying the input XML.
2. Parsing and graph construction use XML metadata generically; no conversion
   logic is conditional on `m_FL_JS_MARTS_CORE` or `CUSTOMERS`.
3. Backward traversal from `CUSTOMERS` selects exactly the two source branches,
   five transformations, and final target described in section 3.2, with no
   unrelated instances.
4. Source instance `STG_ORDERS2` resolves through
   `TRANSFORMATION_NAME="STG_ORDERS"`, not suffix stripping, and emits
   `{{ ref('stg_orders') }}`. `STG_CUSTOMERS` similarly emits
   `{{ ref('stg_customers') }}`.
5. The generated `customers.sql` is one dbt SQL `SELECT` and exposes exactly
   the nine target columns in target order.
6. Fixture execution in DuckDB verifies grouping by customer and the six
   declared aggregate expressions.
7. Fixture execution includes unmatched rows on both join inputs and verifies
   that the Master Outer Join preserves detail/aggregated-order rows, matches
   customer data where available, and does not preserve unmatched master-only
   customers.
8. Null aggregate metrics become zero, and `CUSTOMER_TYPE` is `returning` only
   when the null-normalized lifetime order count is greater than one; otherwise
   it is `new`.
9. An unsupported transformation or configuration reachable from the selected
   target causes a non-zero exit and an error identifying its context.
10. Unsupported content in an independent mapping or unrelated target branch
    does not prevent conversion of the selected target.
11. A selected ancestry requiring a raw source or dbt `source()` resolution
    fails descriptively.
12. Unknown mappings or targets and unsupported reachable transformations
    fail descriptively rather than producing partial SQL.
13. Unit tests cover parsing, metadata-based relation resolution,
    target-specific ancestry traversal, supported SQL rendering, and target
    projection. An integration test uses the supplied XML for the guaranteed
    slice.

Passing these criteria demonstrates only the documented vertical slice. It is
not evidence of general PowerCenter compatibility.