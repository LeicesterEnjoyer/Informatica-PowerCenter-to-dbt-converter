# Development Log

Use this document to record meaningful decisions and evidence during
development. Do not invent entries retrospectively.

## Assumptions

| Date | Assumption | Evidence | Risk |
|---|---|---|---|
| 2026-08-11 | A reached source definition with a same-named XML target definition represents an upstream model that can be referenced with dbt `ref()`. | `STG_ORDERS` and `STG_CUSTOMERS` are produced as staging targets and later consumed as source definitions by the core mapping. | Matching names may not prove model dependency in arbitrary PowerCenter exports; the rule is guaranteed only for the selected vertical slice. |
| 2026-08-11 | Lower-snake-case transformation instance names can serve as deterministic CTE relation identifiers when Milestone 4 composes the individually rendered transformation bodies. | The selected ancestry has distinct instance names after normalization, and the structure tests assert those relation identifiers. | Name collisions after normalization are not handled in the initial slice. |

## Decisions

| Date | Decision | Alternatives considered | Reason |
| --- | --- | --- | --- |
| 2026-08-11 | Initially adopt the agent-proposed frozen dataclasses, tuples, and `MappingProxyType` wrappers for the parsed XML representation. | Use regular dictionaries or retain the XML tree directly. | The proposed representation made the intended read-only data flow explicit and separated later conversion logic from XML parsing. |
| 2026-08-11 | After manually inspecting the parsed model in the debugger, replace the agent-proposed `MappingProxyType` wrappers with regular dictionaries while retaining frozen dataclasses and tuples. | Keep deeply read-only mappings or introduce a custom immutable mapping type. | `MappingProxyType` made the parsed structure harder to inspect while providing no required behaviour for this read-only conversion flow. I chose regular dictionaries to improve transparency and fixture construction, then confirmed through the full test suite that parser behaviour was unchanged. |
| 2026-08-11 | Parse with the Python standard library `ElementTree` and ignore sessions and workflows. | Add an XML dependency or model the complete PowerCenter export. | The supplied file parses without external DTD resolution, and sessions/workflows are outside the approved vertical slice. |
| 2026-08-11 | Use pytest's default temporary-directory handling instead of a fixed workspace-local `--basetemp`. | Keep `.pytest-tmp` under the repository or configure another custom location. | The workspace-local directory produced `PermissionError: [WinError 5]`; removing the custom setting allowed the tests to pass. |
| 2026-08-11 | Build target ancestry from a mapping-local incoming-connector index and retain only instances and connectors reached by walking backward from the selected target. | Validate the complete mapping graph before selecting a target. | The selected `CUSTOMERS` ancestry contains exactly its two source instances, five transformations, and target, while the synthetic unrelated Router branch remains outside the returned graph. |
| 2026-08-11 | Resolve reached source instances by exact `TRANSFORMATION_NAME`, emit `ref()` only when the XML also contains a same-named target definition, and key results by source instance name. | Derive relations from instance names, strip numeric suffixes, or emit `source()` for raw definitions. | The supplied XML resolves `STG_ORDERS2` through definition `STG_ORDERS` and resolves `STG_CUSTOMERS` through its same-named definition. A renamed synthetic instance confirms that instance naming does not affect the resource name. |
| 2026-08-11 | Render individual transformation `SELECT` bodies from connectors and only project ports connected downstream. | Render every declared transformation port or compose the final model during Milestone 3. | This preserves the selected port lineage while keeping final target projection and CTE orchestration in Milestone 4. |
| 2026-08-11 | Recognize Aggregator grouping through `EXPRESSIONTYPE="GROUPBY"` and accept only single-column `COUNT`, `MIN`, `MAX`, and `SUM` expressions. | Build a general aggregate-expression parser. | These are the exact markers and expression shapes observed in `AGG_ORDERS_BY_CUSTOMER`. |
| 2026-08-11 | Derive Joiner master/detail roles and SQL columns from port roles and incoming connector mappings; render Master Outer Join with detail on the SQL left side. | Infer join direction or columns from instance and field names. | The XML marks customer ports as master and maps aggregate `CUSTOMER_ID` into detail port `CUSTOMER_ID1`; structure tests confirm that output `CUSTOMER_ID` remains the connected master value. |
| 2026-08-11 | Translate only identifiers, numeric/string literals, top-level `>`, `ISNULL`, and nested `IIF` using quote-aware, balanced-parenthesis argument splitting. | Use regex substitutions or implement a general PowerCenter expression parser. | A small recursive translator handles the observed expressions without claiming support for broader PowerCenter grammar. |
| 2026-08-11 | Wrap reached transformation and configuration failures with mapping, target, instance, and transformation-type context. | Leak helper exceptions or silently ignore unsupported settings. | Focused tests demonstrated that a plain Joiner configuration `ValueError` lacked selection context before the wrapper was added. |
| 2026-08-11 | Render SQL keywords and aggregate function names in uppercase while retaining lower-snake-case identifiers and lowercase dbt `ref()`. | Preserve the initial all-lowercase SQL output. | A consistent keyword convention improves generated SQL readability without changing its structure or semantics. |
| 2026-08-11 | Use copy-and-replace test fixtures instead of mutating transformation mappings directly. | Mutate the nested dictionary directly or suppress the static type warning. | The models expose transformations through the read-only `Mapping` interface. Rebuilding the affected frozen dataclasses preserves test isolation and avoids contradicting that interface. |

## Coding-agent mistakes

| Date | Agent output or assumption | Why it was wrong | How it was discovered | Correction |
|---|---|---|---|---|
| 2026-08-11 | The agent generated `from src.pwc2dbt.parser import parse_powercenter` in `pwc2dbt/__init__.py`. | In a `src`-layout project, `src` is the package-discovery directory, not part of the import path. The installed package is named `pwc2dbt`. | Pytest failed during test collection with `ModuleNotFoundError: No module named 'src'`. | Replaced the import with the package-relative form `from .parser import parse_powercenter` and reran the complete test suite successfully. |

## Unsupported behaviour

| Feature | Reason excluded | Converter behaviour |
|---|---|---|
| Sessions and workflows | Not required by the selected target conversion or Milestone 1. | Parser ignores these elements. |
| Raw source definitions and dbt `source()` resolution | Excluded from the approved vertical slice. | Relation resolution raises a contextual error when a reached source definition has no matching XML target definition. |
| Source Qualifier overrides, distinct selection, and sorted ports | Only the observed pass-through configuration is supported. | Rendering rejects non-empty SQL/join/filter/pre/post overrides, distinct selection, or nonzero sorted ports. |
| Sorted Aggregator input and aggregate expressions outside the observed subset | Not required by the selected ancestry. | Rendering requires `Sorted Input=NO` and rejects expressions outside direct group-by plus single-column COUNT/MIN/MAX/SUM. |
| Stateful Expression ports and broader expression grammar | Explicitly excluded from the vertical slice. | Rendering rejects variable ports and expression forms outside the documented direct/literal/`>`/`ISNULL`/`IIF` grammar. |
| Joiner types outside the observed unsorted equality Master Outer Join | Other join semantics are not verified for this exercise. | Rendering rejects other join types, sorted input, and non-equality join conditions contextually. |

## Verification performed

| Date | Check | Result |
|---|---|---|
| 2026-08-11 | Initial focused parser test run before production code | Failed during collection with the expected `ModuleNotFoundError: No module named 'pwc2dbt'`. |
| 2026-08-11 | Focused parser tests after implementation | `python -m pytest tests/test_parser.py -q`: 2 passed. |
| 2026-08-11 | Complete test suite after Milestone 1 | `python -m pytest -q`: 2 passed. |
| 2026-08-11 | Initial focused graph test run before production code | Failed during collection with the expected `ModuleNotFoundError: No module named 'pwc2dbt.graph'`. |
| 2026-08-11 | Focused target-ancestry and relation-resolution tests after implementation | `python -m pytest tests/test_graph.py -q`: 7 passed. |
| 2026-08-11 | Complete test suite after Milestone 2 implementation | `python -m pytest -q`: 9 passed. |
| 2026-08-11 | Initial Source Qualifier rendering test | Failed during collection with the expected `ModuleNotFoundError: No module named 'pwc2dbt.rendering'`; after the smallest implementation the focused test passed and the full suite reported 10 passed. |
| 2026-08-11 | Initial Aggregator, Joiner, and Expression rendering tests | Each failed in turn with the expected type-specific `NotImplementedError`; after each smallest implementation the focused/full totals were 2/11, 3/12, and 4/13 passed respectively. |
| 2026-08-11 | Initial unsupported-transformation test | Failed during collection because `RenderingError` did not exist; after adding contextual type rejection the focused tests reported 5 passed and the full suite 14 passed. |
| 2026-08-11 | Initial unsupported Joiner configuration test | Failed with a plain `ValueError: Only Master Outer Join is supported`; after contextual wrapping the focused tests reported 6 passed and the full suite 15 passed. |
| 2026-08-11 | Initial stateful Expression, Source Qualifier filter, and sorted Aggregator tests | Each failed because no error was raised; after each focused guard the final rendering tests reported 9 passed and the full suite 18 passed. |
| 2026-08-11 | SQL casing convention refactor | Updated rendering expectations failed in the four structure tests because emitted SQL still used lowercase tokens; after changing only keyword and aggregate-function casing, the focused suite reported 9 passed and the full suite 18 passed. |
