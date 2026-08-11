# Development Log

Use this document to record meaningful decisions and evidence during
development. Do not invent entries retrospectively.

## Assumptions

| Date | Assumption | Evidence | Risk |
|---|---|---|---|
| 2026-08-11 | A reached source definition with a same-named XML target definition represents an upstream model that can be referenced with dbt `ref()`. | `STG_ORDERS` and `STG_CUSTOMERS` are produced as staging targets and later consumed as source definitions by the core mapping. | Matching names may not prove model dependency in arbitrary PowerCenter exports; the rule is guaranteed only for the selected vertical slice. |

## Decisions

| Date | Decision | Alternatives considered | Reason |
| --- | --- | --- | --- |
| 2026-08-11 | Initially adopt the agent-proposed frozen dataclasses, tuples, and `MappingProxyType` wrappers for the parsed XML representation. | Use regular dictionaries or retain the XML tree directly. | The proposed representation made the intended read-only data flow explicit and separated later conversion logic from XML parsing. |
| 2026-08-11 | After manually inspecting the parsed model in the debugger, replace the agent-proposed `MappingProxyType` wrappers with regular dictionaries while retaining frozen dataclasses and tuples. | Keep deeply read-only mappings or introduce a custom immutable mapping type. | `MappingProxyType` made the parsed structure harder to inspect while providing no required behaviour for this read-only conversion flow. I chose regular dictionaries to improve transparency and fixture construction, then confirmed through the full test suite that parser behaviour was unchanged. |
| 2026-08-11 | Parse with the Python standard library `ElementTree` and ignore sessions and workflows. | Add an XML dependency or model the complete PowerCenter export. | The supplied file parses without external DTD resolution, and sessions/workflows are outside the approved vertical slice. |
| 2026-08-11 | Use pytest's default temporary-directory handling instead of a fixed workspace-local `--basetemp`. | Keep `.pytest-tmp` under the repository or configure another custom location. | The workspace-local directory produced `PermissionError: [WinError 5]`; removing the custom setting allowed the tests to pass. |
| 2026-08-11 | Build target ancestry from a mapping-local incoming-connector index and retain only instances and connectors reached by walking backward from the selected target. | Validate the complete mapping graph before selecting a target. | The selected `CUSTOMERS` ancestry contains exactly its two source instances, five transformations, and target, while the synthetic unrelated Router branch remains outside the returned graph. |
| 2026-08-11 | Resolve reached source instances by exact `TRANSFORMATION_NAME`, emit `ref()` only when the XML also contains a same-named target definition, and key results by source instance name. | Derive relations from instance names, strip numeric suffixes, or emit `source()` for raw definitions. | The supplied XML resolves `STG_ORDERS2` through definition `STG_ORDERS` and resolves `STG_CUSTOMERS` through its same-named definition. A renamed synthetic instance confirms that instance naming does not affect the resource name. |

## Coding-agent mistakes

| Date | Agent output or assumption | Why it was wrong | How it was discovered | Correction |
|---|---|---|---|---|
| 2026-08-11 | The agent generated `from src.pwc2dbt.parser import parse_powercenter` in `pwc2dbt/__init__.py`. | In a `src`-layout project, `src` is the package-discovery directory, not part of the import path. The installed package is named `pwc2dbt`. | Pytest failed during test collection with `ModuleNotFoundError: No module named 'src'`. | Replaced the import with the package-relative form `from .parser import parse_powercenter` and reran the complete test suite successfully. |

## Unsupported behaviour

| Feature | Reason excluded | Converter behaviour |
|---|---|---|
| Sessions and workflows | Not required by the selected target conversion or Milestone 1. | Parser ignores these elements. |
| Raw source definitions and dbt `source()` resolution | Excluded from the approved vertical slice. | Relation resolution raises a contextual error when a reached source definition has no matching XML target definition. |

## Verification performed

| Date | Check | Result |
|---|---|---|
| 2026-08-11 | Initial focused parser test run before production code | Failed during collection with the expected `ModuleNotFoundError: No module named 'pwc2dbt'`. |
| 2026-08-11 | Focused parser tests after implementation | `python -m pytest tests/test_parser.py -q`: 2 passed. |
| 2026-08-11 | Complete test suite after Milestone 1 | `python -m pytest -q`: 2 passed. |
| 2026-08-11 | Initial focused graph test run before production code | Failed during collection with the expected `ModuleNotFoundError: No module named 'pwc2dbt.graph'`. |
| 2026-08-11 | Focused target-ancestry and relation-resolution tests after implementation | `python -m pytest tests/test_graph.py -q`: 7 passed. |
| 2026-08-11 | Complete test suite after Milestone 2 implementation | `python -m pytest -q`: 9 passed. |
