# Informatica PowerCenter to dbt Converter

A deliberately scoped converter that reads an Informatica PowerCenter XML
export and writes a dbt SQL model derived from the selected target's connector
ancestry.

## Requirements and installation

- Python 3.11 or newer.
- DuckDB and pytest are required only for development and integration tests.

Create and activate a virtual environment:

```powershell
python -m venv .venv .\.venv\Scripts\Activate.ps1
```

Install the package and development dependencies from the repository root:

```text
python -m pip install -e ".[dev]"
```

## Running the converter

The guaranteed vertical slice is target `CUSTOMERS` in mapping
`m_FL_JS_MARTS_CORE`. Run it with:

```text
python -m pwc2dbt data/FLOWLINE_DEMO_JAFFLESHOP.xml --mapping m_FL_JS_MARTS_CORE --target CUSTOMERS --output models/customers.sql
```

The command writes one UTF-8 dbt SQL model. It exits nonzero and prints a
descriptive error if the selected ancestry requires unsupported behavior.
Mapping and target names are arguments, not special cases in conversion code;
another target may work if its complete reachable ancestry uses only the same
supported configurations.

Run the test suite with:

```text
python -m pytest -q
```

## Supported behavior

The converter parses definitions, mappings, transformations, instances,
fields, attributes, and connectors. It walks backward from only the selected
target and supports the configurations observed in the guaranteed slice:

- pass-through Source Qualifiers backed by metadata-resolved dbt `ref()` calls;
- unsorted Aggregators using direct group-by ports and single-column `COUNT`,
  `MIN`, `MAX`, and `SUM`;
- the unsorted equality-based Master Outer Join, preserving the detail input;
- stateless Expressions using direct ports, literals, `>`, `ISNULL`, and nested
  `IIF`;
- connector-driven final projection in XML target-field order.

The integration test replaces the two dbt `ref()` expressions with fixture
table names and executes the resulting SQL in an in-memory DuckDB database. It
verifies SQL validity, aggregation, null normalization, returning/new
classification, and that unmatched detail rows survive with a null master
`customer_id`. It does not execute dbt itself or validate a complete dbt
project.

## Assumptions

- A source definition with a same-named XML target definition represents an
  upstream dbt model suitable for `ref()`.
- Lower-snake-case normalization is suitable for dbt resource, relation, and
  column names.
- The selected source and target datatypes do not require explicit casts in
  DuckDB.
- SQL aggregates, null checks, and conditional expressions match PowerCenter
  for the tested fixture values; this is not a general equivalence claim.

## Intentional exclusions

- raw source definitions, dbt source YAML, and dbt `source()` resolution;
- Router, Union, Sorter, Filter, Lookup, and general Custom transformations;
- stateful or local-variable Expression ports and general expression parsing;
- Source Qualifier SQL, filter, join, distinct, sorted-port, and pre/post-SQL
  overrides;
- sorted or incremental aggregation and unobserved Joiner configurations;
- sessions, workflows, scheduling, connections, loading modes, reject handling,
  and target pre/post-SQL;
- dbt project scaffolding, materializations, tests, and documentation generation;
- general Oracle-to-DuckDB datatype and function conversion.

Unsupported constructs fail only when reachable from the selected target.
Unsupported independent mappings and unrelated target branches do not block
conversion.

## Likely incorrect-output areas

The matching source/target-name rule may not identify dbt dependencies in
arbitrary PowerCenter exports. Normalized names may collide, and untested
datatypes or null/function semantics may differ between PowerCenter and the
destination database. Only `m_FL_JS_MARTS_CORE.CUSTOMERS` is guaranteed and
integration-tested; successful output for another target is not a semantic
equivalence guarantee.

The supplied XML marks the customer input as master and the aggregated-order
input as detail in a Master Outer Join. PowerCenter therefore preserves
aggregated-order rows, which excludes customers without orders and may produce
null customer fields for orders without a matching customer. The converter
intentionally follows the XML configuration rather than correcting its
apparent business intent.

## Coding-agent mistake caught during development

The coding agent initially generated `from src.pwc2dbt.parser` in the package
initializer. In a src-layout project, `src` is a package-discovery directory,
not part of the import name, so pytest failed with `ModuleNotFoundError`. The
import was corrected to `from .parser`, and the complete suite was rerun.

Detailed scope and implementation evidence are in
[`docs/SPEC.md`](docs/SPEC.md), [`docs/PLAN.md`](docs/PLAN.md), and
[`docs/DEVELOPMENT_LOG.md`](docs/DEVELOPMENT_LOG.md).
