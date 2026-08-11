# Agent Instructions

## Required reading

Before making changes, read:

1. `docs/ASSIGNMENT.md`
2. `docs/SPEC.md`, if it exists
3. `docs/PLAN.md`, if it exists
4. `docs/DEVELOPMENT_LOG.md`

Inspect `data/FLOWLINE_DEMO_JAFFLESHOP.xml` whenever PowerCenter behaviour
must be verified.

## Development workflow

Follow a specification-driven and test-first approach.

For every behaviour:

1. Write a failing test describing the expected behaviour.
2. Run the test and confirm that it fails for the expected reason.
3. Implement the smallest change that makes the test pass.
4. Run the relevant tests.
5. Run the complete test suite.
6. Refactor only while all tests remain passing.

Do not implement work that is not included in the approved `docs/PLAN.md`.

## Project constraints

- Derive conversion output from the XML structure.
- Prefer explicit errors over silently incorrect SQL.
- Support only functionality justified by the provided sample.
- Separate XML parsing, mapping representation, graph traversal, expression
  translation, and SQL generation where practical.
- Do not claim semantic equivalence without tests or documented manual
  verification.
- Do not modify the provided XML input.

## Verification

Before declaring a task complete:

- Run the full test suite.
- Confirm that the CLI works with the provided XML.
- Inspect the generated SQL.
- Review the diff for hard-coded sample-specific logic.
- Update `docs/DEVELOPMENT_LOG.md` with important decisions, assumptions,
  and limitations.

## Definition of done

The project is complete when:

- The converter can be run from the command line.
- It reads a PowerCenter XML export and generates dbt SQL models.
- Tests cover the supported parsing and conversion behaviour.
- Unsupported behaviour produces descriptive errors.
- All tests pass.
- The README explains how to run the project.