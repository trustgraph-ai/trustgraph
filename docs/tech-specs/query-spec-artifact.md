---
layout: default
title: "QuerySpecArtifact Technical Specification"
parent: "Tech Specs"
---

# QuerySpecArtifact Technical Specification

## Overview

This specification defines QuerySpecArtifact, a structured query
representation used by the execution framework to separate query
formulation (LLM-powered) from query execution (store-specific).

An LLM-powered `query-formulate` capability translates natural language
into a QuerySpecArtifact. Store-specific data services (e.g.
`erp-finance`) accept the spec and execute it against their own storage.
A mechanical `query-join` capability combines two QuerySpecArtifacts
into a single joined spec.

## Goals

- **Separate concerns**: LLM reasoning about what data is needed
  stays in the generic `query-formulate` step; store-specific
  execution stays in the data service.
- **Explicit column selection**: queries always declare the columns
  they need, supporting downstream resolution and avoiding
  unbounded result sets.
- **Composable joins**: the spec is a tree structure where leaves
  are single-table selects and internal nodes are joins, allowing
  multi-table queries to be built incrementally.
- **Auditable**: the spec is a plain JSON document that can be
  logged, policy-checked and inspected between pipeline steps.
- **LLM-friendly**: constrained enough that an LLM can reliably
  produce valid specs from a schema description.

## Background

The execution framework's planner decomposes a user question into
capability steps.  For structured data queries, the planner selects
the data source but should not construct detailed queries — that
requires schema knowledge and is better handled by an LLM with the
schema in context.

Currently, data services like `erp-finance` accept simple params
(e.g. `table=headcount`).  This returns entire tables.  For
production use with large datasets, we need filtering, column
selection, ordering and limits.  QuerySpecArtifact provides a
structured intermediate representation for this.

## Execution Flow

```
question
  -> planner (decomposes, picks data sources)
    -> query-formulate (generic LLM + schema -> QuerySpecArtifact)
      -> data-service (store-specific, executes spec -> TabularArtifact)
```

For joins:

```
question
  -> planner
    -> query-formulate -> QuerySpecArtifact (table A)
    -> query-formulate -> QuerySpecArtifact (table B)
      -> query-join (mechanical, combines specs -> QuerySpecArtifact)
        -> data-service (executes joined spec -> TabularArtifact)
```

## QuerySpecArtifact Format

### Select (v1)

A single-table query with column selection, filtering, ordering and
a row limit.

```json
{
  "version": "1",
  "type": "select",
  "table": "headcount",
  "columns": ["department", "fte", "headcount"],
  "filters": [
    {"column": "department", "op": "eq", "value": "Engineering"},
    {"column": "fte", "op": "gte", "value": 10}
  ],
  "order_by": [
    {"column": "fte", "direction": "desc"}
  ],
  "limit": 100
}
```

#### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `version` | string | yes | Spec version.  Always `"1"`. |
| `type` | string | yes | `"select"` for a single-table query. |
| `table` | string | yes | Table name, matching a schema name in the data source. |
| `columns` | list of string | yes | Columns to return.  Must not be empty. |
| `filters` | list of filter | no | Row filter conditions.  All conditions are ANDed. |
| `order_by` | list of ordering | no | Sort order.  Applied in list order. |
| `limit` | integer | no | Maximum rows to return. |

#### Filter

| Field | Type | Required | Description |
|---|---|---|---|
| `column` | string | yes | Column name to filter on. |
| `op` | string | yes | Operator.  One of: `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `in`, `like`. |
| `value` | string, number, or list | yes | Comparison value.  `in` expects a list; all others expect a scalar. |

#### Ordering

| Field | Type | Required | Description |
|---|---|---|---|
| `column` | string | yes | Column name to sort by. |
| `direction` | string | yes | `"asc"` or `"desc"`. |

### Join (v1)

Combines two query specs on a shared key.  The left and right
children can be selects or nested joins, forming a tree.

```json
{
  "version": "1",
  "type": "join",
  "join_type": "inner",
  "left": {
    "type": "select",
    "table": "headcount",
    "columns": ["department", "fte"],
    "filters": []
  },
  "right": {
    "type": "select",
    "table": "workforce_budget",
    "columns": ["department", "budget_q3"],
    "filters": []
  },
  "on": [
    {"left": "department", "right": "department"}
  ]
}
```

#### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `version` | string | yes | Spec version.  Always `"1"`. |
| `type` | string | yes | `"join"`. |
| `join_type` | string | yes | `"inner"`, `"left"`, `"right"`, or `"outer"`. |
| `left` | QuerySpec | yes | Left side of the join (select or nested join). |
| `right` | QuerySpec | yes | Right side of the join (select or nested join). |
| `on` | list of join key | yes | Column pairs to join on.  Must not be empty. |

#### Join key

| Field | Type | Required | Description |
|---|---|---|---|
| `left` | string | yes | Column name from the left side. |
| `right` | string | yes | Column name from the right side. |

## Schema Discovery

The `query-formulate` capability needs access to table schemas to
produce valid specs.  Schemas are stored in TrustGraph using the
existing structured data schema mechanism.  A schema describes
available tables, their columns, types, and key relationships.

Example schema entry:

```json
{
  "name": "headcount",
  "description": "Employee headcount by department and role",
  "fields": [
    {
      "name": "department",
      "type": "string",
      "primary_key": false,
      "required": true,
      "description": "Department name"
    },
    {
      "name": "fte",
      "type": "number",
      "primary_key": false,
      "required": true,
      "description": "Full-time equivalent count"
    }
  ]
}
```

Foreign key markers in schemas enable the `query-join` step to
determine join columns mechanically without LLM involvement.  The
exact foreign key representation is TBD.

## Capabilities

### query-formulate (generic, LLM-powered)

- **Input**: natural language sub-question (from planner via params),
  schema name (param)
- **Process**: fetches the schema from TrustGraph, constructs an LLM
  prompt with the schema and question, parses the LLM response into
  a QuerySpecArtifact
- **Output**: QuerySpecArtifact

### query-join (generic, mechanical)

- **Input**: two QuerySpecArtifacts
- **Process**: inspects schemas for FK/PK relationships, produces a
  joined QuerySpecArtifact with the appropriate `on` clause
- **Output**: QuerySpecArtifact

### Data services (store-specific)

Each data service (e.g. `erp-finance`) accepts a QuerySpecArtifact
as input and executes it against its own storage, returning a
TabularArtifact.  The service is responsible for validating the spec
against its own schema and translating it into native queries.

## Future Extensions

- **Aggregation**: `group_by` with aggregate functions (`sum`,
  `count`, `avg`, `min`, `max`) on the select type.
- **Subqueries**: nested selects in filter values.
- **Cross-source joins**: joins where left and right reference
  different data services, requiring separate fetches and an
  in-memory join of TabularArtifacts.

## Open Questions

- Exact foreign key representation in schemas — inline on the
  field, or a separate `foreign_keys` section?
- Should `query-join` infer join keys from FK/PK only, or accept
  an explicit join-key hint from the planner?
- How does the planner communicate which schema to use to
  `query-formulate` — a param, or derived from the data source
  capability name?
