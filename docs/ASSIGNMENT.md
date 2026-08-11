# Original Assignment

This document contains the original assignment exactly as received. It is a
source requirement and must not be modified to match the implementation.

---

# Take-home Exercise: Informatica PowerCenter to dbt Converter

This exercise is part of our interview process for the Product Engineer
(Associate) role.

- **Expected effort:** Approximately 4 hours

## What We Are Asking

Build a small tool that converts an Informatica PowerCenter mapping into an
equivalent dbt model.

We have attached one sample PowerCenter mapping file in XML to work from:

- [PowerCenter demo XML workflow](https://github.com/infinitelambda/flowline-pwc-demo)

The mapping mirrors the public dbt Jaffle Shop demo project. You can use that
project as a reference target: run it, inspect its models, and compare your
converter's output against it.

- [Jaffle Shop DuckDB reference project](https://github.com/dbt-labs/jaffle_shop_duckdb)

Your converter must derive the dbt model from the XML. Do not hard-code the
Jaffle Shop output, because we are assessing the conversion logic rather than
the final SQL.

You are not expected to know either Informatica PowerCenter or dbt in advance.
Part of what we want to see is how you get up to speed with an unfamiliar
system. The resources below are enough to get started.

## Background

### Informatica PowerCenter

Informatica PowerCenter is an ETL tool. A mapping describes how data moves from
source tables to target tables through a chain of transformations, such as:

- filters;
- joins;
- lookups;
- aggregations;
- other data transformations.

Mappings can be exported as XML, which is the provided input format.

Resources:

- [Mappings overview](https://docs.informatica.com/data-integration/powercenter/10-5/designer-guide/mappings/mappings-overview.html)
- [Transformation guide](https://docs.informatica.com/data-integration/powercenter/10-5/transformation-guide/preface.html)

### dbt

dbt transforms data that is already stored in a data warehouse by using SQL.

A dbt model is a single SQL `SELECT` statement stored in a `.sql` file. dbt can
materialize a model as a table or view. Models can reference one another and
can include tests and documentation.

Resources:

- [What is dbt?](https://docs.getdbt.com/docs/introduction)
- [About dbt models](https://docs.getdbt.com/docs/build/models)
- [SQL models](https://docs.getdbt.com/docs/build/sql-models)
- [dbt quickstart guides](https://docs.getdbt.com/guides)

The Jaffle Shop reference project can be run locally with DuckDB:

- [Jaffle Shop DuckDB](https://github.com/dbt-labs/jaffle_shop_duckdb)

## The Task

1. Read the sample PowerCenter XML and determine what the mapping does.
2. Build a converter, using any programming language, that:
   - reads a PowerCenter mapping XML file;
   - produces an equivalent dbt model.
3. Include tests.
4. Where useful, check the generated output against the Jaffle Shop reference
   project.
5. Handle what you reasonably can within the available time.

We care more about how you reason about the problem than about complete
PowerCenter feature coverage.

## Using Coding Agents

We expect you to use coding agents such as Claude Code or Cursor. This is how
the team works day to day, and we want to see how you use them.

If you do not have access to a tool, tell us. We may be able to provide access
or refund your expenses.

## What to Submit

Submit one of the following:

- a public GitHub repository;
- a private GitHub repository with access granted to the provided GitHub
  handles;
- a zipped project folder.

Include a short `README.md` that explains:

- how to run the converter;
- what you assumed;
- what you chose not to handle;
- where the converter is most likely to produce incorrect output;
- where a coding agent produced something incorrect and how you caught it.

## What We Are Looking For

- You understand the submitted code and can explain any part of it.
- The conversion is handled sensibly.
- You have a clear understanding of where the converter works and where it
  breaks.
- The README communicates your reasoning clearly.

## Logistics

- **Effort:** Approximately 4 hours
- **Important:** Please do not over-invest.