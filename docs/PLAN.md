# TDD Implementation Plan

## Approach and time box

Budget: **three hours**. Schedule 170 minutes across four sequential milestones
and reserve a final **10-minute debugging buffer**. Use Python >=3.11,
`xml.etree.ElementTree`, dataclasses, pytest, and DuckDB. Keep parsing, graph
traversal, relation resolution, and rendering driven by XML metadata; mapping
and target names appear only in tests and CLI arguments.

Every milestone is a strict TDD gate. For each behavior, in this order:

1. Write the focused test before production code.
2. Run the focused test and confirm it fails for the reason stated in the
   milestone—not because of a broken test or environment.
3. Implement the smallest production change required to pass.
4. Run the focused test and confirm it passes.
5. Run the full test suite and confirm it passes.
6. Refactor only while all tests remain passing, rerunning the focused and full
   suites after any refactor.

Do not write production code before its corresponding failing test has been
observed. Do not use the debugging buffer to add scope.

## Milestone 1 — Required XML parser and representation (25 minutes)

- **Behavior:** Parse source and target definitions, mappings,
  transformations, transform fields/groups/attributes, instances, and
  connectors into generic dataclasses. Preserve names, types, port roles,
  expressions, and connector endpoints needed by the supported slice.
- **Failing test first:**
  `tests/test_parser.py::test_parses_required_powercenter_elements` uses a
  small synthetic export and asserts the definitions, instances,
  transformation configuration, fields, and connectors. Add a supplied-XML
  smoke test that finds `m_FL_JS_MARTS_CORE` and target `CUSTOMERS`.
- **Why it initially fails:** The `pwc2dbt` package and parser API do not
  exist.
- **Smallest implementation:** Add project metadata requiring Python >=3.11,
  with pytest and DuckDB as development dependencies; add immutable dataclasses
  and an ElementTree parser that does not resolve the external DTD. Do not
  parse sessions or workflows.
- **Verification commands:**

  ```powershell
  # Before implementation: confirm the expected failure.
  python -m pytest tests/test_parser.py -q
  # After the smallest implementation: focused and full suites must pass.
  python -m pytest tests/test_parser.py -q
  python -m pytest -q
  ```

- **Completion criteria:** Both parser tests pass; the representation contains
  all metadata required by later milestones and no mapping- or target-name
  branches.

## Milestone 2 — Target ancestry and metadata-based refs (35 minutes)

- **Behavior:** Given mapping and target names, follow incoming connectors
  backward and retain only the selected ancestry. Resolve each reached source
  instance through `TRANSFORMATION_NAME` to a source definition, require a
  matching target definition, normalize that definition name, and produce a
  dbt `ref()`. Unrelated valid branches and unsupported transformations
  outside the ancestry are ignored.
- **Failing test first:** Add:
  - `tests/test_graph.py::test_builds_only_selected_target_ancestry`, with an
    unsupported transformation on an unselected branch;
  - a supplied-XML assertion for the exact `CUSTOMERS` ancestry;
  - `tests/test_graph.py::test_resolves_ref_from_source_definition_metadata`,
    asserting that instance `STG_ORDERS2` resolves through
    `TRANSFORMATION_NAME="STG_ORDERS"` to
    `{{ ref('stg_orders') }}`, even if the instance is renamed.
- **Why it initially fails:** Parsed connectors have no selected-target walk,
  and source instances have no relation resolver.
- **Smallest implementation:** Build an incoming-edge index for the requested
  mapping, perform a visited-set backward walk, and validate only reached
  references. Add exact source-definition lookup by `TRANSFORMATION_NAME`,
  matching-target lookup, conservative lower-snake-case normalization, and a
  contextual unsupported-source error. Do not strip instance suffixes or
  implement raw sources/`source()`.
- **Verification commands:**

  ```powershell
  # Before implementation: confirm the expected failure.
  python -m pytest tests/test_graph.py -q
  # After the smallest implementation: focused and full suites must pass.
  python -m pytest tests/test_graph.py -q
  python -m pytest -q
  ```

- **Completion criteria:** The supplied slice contains exactly two source
  instances, five transformations, and the final target; unrelated branches do
  not block it; `STG_ORDERS2` and `STG_CUSTOMERS` yield
  `ref('stg_orders')` and `ref('stg_customers')`; unknown selections and
  unsupported sources fail descriptively.

## Milestone 3 — Structure-only transformation rendering (55 minutes)

- **Behavior:** Render capability-driven SQL CTEs for the observed pass-through
  Source Qualifier, unsorted Aggregator, equality-based Master Outer Join, and
  stateless Expression configurations. Unit tests inspect SQL structure only;
  they do not execute DuckDB.
- **Failing test first:** Add focused tests in
  `tests/test_rendering.py`, one at a time, for:
  1. Source Qualifier projection from a resolved `ref()`;
  2. group-by with the observed `COUNT`, `MIN`, `MAX`, and `SUM`;
  3. aggregated detail SQL left-joining customer master SQL;
  4. direct ports, null-to-zero expressions, and returning/new classification;
  5. contextual failure for a reachable unsupported configuration.
- **Why it initially fails:** No renderer dispatch, expression translator, or
  CTE composition exists. Each next test fails because only the preceding
  capability has been implemented.
- **Smallest implementation:** Add checked renderer dispatch and deterministic
  CTE aliases. Translate only direct ports/literals, `>`, and the observed
  nested `IIF`/`ISNULL` grammar. Use a balanced-parenthesis argument splitter:
  scan characters, track quote state and parenthesis depth, and split arguments
  only at depth-zero commas. Accept only the documented shapes and reject the
  rest; do not build a general regex expression parser. Render the master-outer
  join with detail on the preserved left side. Project `CUSTOMER_ID` from the
  master port exactly as connected—never coalesce or substitute detail
  `CUSTOMER_ID1`.
- **Verification commands:**

  ```powershell
  # Before each renderer capability: run its focused test and confirm failure.
  python -m pytest tests/test_rendering.py -q
  # After each smallest change: focused and full suites must pass.
  python -m pytest tests/test_rendering.py -q
  python -m pytest -q
  ```

- **Completion criteria:** Structure assertions cover all supported
  transformations and exact target-port lineage; no DuckDB execution occurs in
  these tests; unsupported shapes fail; renderer code contains no mapping- or
  target-name checks.

## Milestone 4 — Integration, README, and final review (55 minutes)

- **Behavior:** Spend at most 30 minutes projecting fields in target order,
  exposing the CLI, converting the supplied XML to `customers.sql`, and
  executing a compiled test form in in-memory DuckDB. Reserve the remaining
  25 minutes for README completion, development evidence, the final suite, CLI
  and SQL inspection, and diff review. The command contract is:

  ```text
  python -m pwc2dbt <xml> --mapping <name> --target <name> --output <file>
  ```

- **Failing test first:** First add
  `tests/test_integration.py::test_converts_core_customers_from_supplied_xml`
  invokes the CLI entry function with a temporary output, asserts one dbt
  `SELECT`, both metadata-derived refs, and the nine target columns in XML
  order, then replaces only those refs with fixture relations and executes the
  SQL in DuckDB. The fixture includes unmatched master and detail rows. It
  asserts that the unmatched detail row survives while its projected
  `CUSTOMER_ID` remains null because the target is connected to the master
  `CUSTOMER_ID`, not detail `CUSTOMER_ID1`. After integration passes, add
  `tests/test_readme.py::test_readme_documents_supported_cli_and_limits`,
  requiring the runnable command, guaranteed slice, assumptions, exclusions,
  likely incorrect-output areas, and coding-agent mistake discussion.
- **Why it initially fails:** The renderer lacks final target projection,
  orchestration, argument parsing, and file output, so the integration test
  fails first. The current README then fails its test because it does not yet
  document the implemented CLI and final behavior completely.
- **Smallest implementation:** Add connector-driven target aliases, top-level
  conversion orchestration, `argparse`, `__main__`, UTF-8 output, and
  contextual non-zero error handling. Add only the DuckDB fixture compilation
  shim; do not generate a dbt project or source YAML. Then update README to
  match actual commands, assumptions, exclusions, and limitations, and record
  only contemporaneous evidence in `docs/DEVELOPMENT_LOG.md`.
- **Verification commands:**

  ```powershell
  # Before CLI/integration implementation: confirm the expected failure.
  python -m pytest tests/test_integration.py -q
  # After the smallest integration change: focused and full suites must pass.
  python -m pytest tests/test_integration.py -q
  python -m pytest -q
  # Before README edits: confirm the focused documentation test fails.
  python -m pytest tests/test_readme.py -q
  # After the smallest README edit: focused and full suites must pass.
  python -m pytest tests/test_readme.py -q
  python -m pytest -q
  python -m pwc2dbt data/FLOWLINE_DEMO_JAFFLESHOP.xml --mapping m_FL_JS_MARTS_CORE --target CUSTOMERS --output "$env:TEMP\customers.sql"
  Get-Content -Raw "$env:TEMP\customers.sql"
  git diff --check
  git status --short
  git diff
```

- **Completion criteria:** DuckDB verifies aggregation, exact master/detail
  behavior, null normalization, and classification; the CLI exits zero; the
  model has exactly nine projected columns; README instructions run as written
  and cover every assignment disclosure; the development log reflects actual
  work; the input XML is unchanged; and the reviewed diff contains no
  hard-coded Jaffle output or work outside the approved specification.

## Debugging buffer and exclusions

Reserve the final 10 minutes only for diagnosing or fixing failures in the four
milestones. Do not schedule cycle detection, ambiguous duplicate-definition
handling, malformed unrelated-mapping validation, exhaustive connector
validation, raw source/`source()` support, or unsupported transformations. If
the buffer is unused, stop early rather than broaden scope.
