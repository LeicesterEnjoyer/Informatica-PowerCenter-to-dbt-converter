# Development Log

Use this document to record meaningful decisions and evidence during
development. Do not invent entries retrospectively.

## Assumptions

| Date | Assumption | Evidence | Risk |
|---|---|---|---|

## Decisions

| Date | Decision | Alternatives considered | Reason |
| --- | --- | --- | --- |
| 2026-08-11 | Initially adopt the agent-proposed frozen dataclasses, tuples, and `MappingProxyType` wrappers for the parsed XML representation. | Use regular dictionaries or retain the XML tree directly. | The proposed representation made the intended read-only data flow explicit and separated later conversion logic from XML parsing. |
| 2026-08-11 | Replace the agent-proposed `MappingProxyType` wrappers with regular dictionaries while retaining frozen dataclasses and tuples. | Keep deeply read-only mappings or introduce a custom immutable mapping type. | During debugging, `MappingProxyType` made the parsed structure harder to inspect while providing no necessary behaviour for this read-only conversion flow. Regular dictionaries improved transparency without changing parser results, as confirmed by the full test suite. |
| 2026-08-11 | Parse with the Python standard library `ElementTree` and ignore sessions and workflows. | Add an XML dependency or model the complete PowerCenter export. | The supplied file parses without external DTD resolution, and sessions/workflows are outside the approved vertical slice. |
| 2026-08-11 | Use pytest's default temporary-directory handling instead of a fixed workspace-local `--basetemp`. | Keep `.pytest-tmp` under the repository or configure another custom location. | The workspace-local directory produced `PermissionError: [WinError 5]`; removing the custom setting allowed the tests to pass. |

## Coding-agent mistakes

| Date | Agent output or assumption | Why it was wrong | How it was discovered | Correction |
|---|---|---|---|---|
| 2026-08-11 | The agent generated `from src.pwc2dbt.parser import parse_powercenter` in `pwc2dbt/__init__.py`. | In a `src`-layout project, `src` is the package-discovery directory, not part of the import path. The installed package is named `pwc2dbt`. | Pytest failed during test collection with `ModuleNotFoundError: No module named 'src'`. | Replaced the import with the package-relative form `from .parser import parse_powercenter` and reran the complete test suite successfully. |

## Unsupported behaviour

| Feature | Reason excluded | Converter behaviour |
|---|---|---|
| Sessions and workflows | Not required by the selected target conversion or Milestone 1. | Parser ignores these elements. |

## Verification performed

| Date | Check | Result |
|---|---|---|
| 2026-08-11 | Initial focused parser test run before production code | Failed during collection with the expected `ModuleNotFoundError: No module named 'pwc2dbt'`. |
| 2026-08-11 | Focused parser tests after implementation | `python -m pytest tests/test_parser.py -q`: 2 passed. |
| 2026-08-11 | Complete test suite after Milestone 1 | `python -m pytest -q`: 2 passed. |
