# Informatica PowerCenter to dbt Converter

A small tool that converts supported Informatica PowerCenter mappings exported
as XML into dbt SQL models.

This project is being developed as part of a take-home exercise for the Product
Engineer (Associate) role at Infinite Lambda.

## Project Status

The project is currently in the specification and planning phase.

Implementation will follow a specification-driven and test-first development
approach. The supported conversion scope will be determined after analysing the
provided PowerCenter XML mapping.

## Repository Structure

```text
├── data/
│   └── FLOWLINE_DEMO_JAFFLESHOP.xml
├── docs/
│   ├── ASSIGNMENT.md
│   ├── DEVELOPMENT_LOG.md
│   ├── PLAN.md
│   └── SPEC.md
├── AGENTS.md
├── LICENSE
└── README.md
```

Additional source code, tests, specifications, and implementation plans will be
added as development progresses.

## Documentation

- [Original assignment](docs/ASSIGNMENT.md)
- [Development log](docs/DEVELOPMENT_LOG.md)

The technical specification and implementation plan will be created after
analysing the assignment and supplied XML mapping.

## Sample Input

The provided PowerCenter repository export is located at:

```text
data/FLOWLINE_DEMO_JAFFLESHOP.xml
```

It represents a Jaffle Shop data pipeline flowing through the following layers:

```text
RAW → staging → core marts → enriched marts
```

The original dbt project is available at:

- [Jaffle Shop DuckDB](https://github.com/dbt-labs/jaffle_shop_duckdb)

## Development Approach

The project follows a specification-driven and test-first workflow:

1. Analyse the assignment and PowerCenter XML.
2. Define the supported conversion behaviour.
3. Create a time-boxed implementation plan.
4. Implement each behaviour using TDD.
5. Validate the generated SQL against the reference project where practical.
6. Document assumptions, unsupported behaviour, and likely failure points.

## Running the Project

Installation and usage instructions will be added after the initial
implementation.