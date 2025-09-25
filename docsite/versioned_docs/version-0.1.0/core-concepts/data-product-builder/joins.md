---
sidebar_position: 6
title: Joins
---

# Handling Joins

> All examples on this and subsequent pages use the sample [healthcare dataset](https://github.com/Intugle/data-tools/tree/main/sample_data/healthcare) available in the project repository.

One of the most powerful features of the `DataProductBuilder` is its ability to automatically handle joins between tables. You don't need to write explicit `JOIN` clauses; the builder infers the required joins based on the fields you select and the relationships defined in the semantic layer.

## Implicit Joins

When you select fields from multiple tables in your `product_spec`, the `DataProductBuilder` automatically finds the shortest, most logical path to connect them. It uses the relationships discovered by the `KnowledgeBuilder` to construct the necessary `JOIN` clauses.

### Syntax

To trigger a join, simply include `id`s from two or more different tables in your `fields` list.

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        {"id": "table_a.column_1", "name": "field_from_table_a"},
        {"id": "table_b.column_2", "name": "field_from_table_b"},
    ],
}
```

### Example

This example creates a data product that combines patient information with their medical conditions. By selecting `patients.first` and `conditions.description`, you implicitly tell the builder to join the `patients` and `conditions` tables.

```python
product_spec = {
    "name": "patient_conditions",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {"id": "conditions.description", "name": "condition"},
    ],
    "filter": {"limit": 5}
}
```

#### Generated SQL

The `DataProductBuilder` inspects the semantic layer and finds that `patients.id` is linked to `conditions.patient`. It then generates the appropriate `JOIN` clause automatically.

```sql
SELECT
  "patients"."first" as first_name,
  "patients"."last" as last_name,
  "conditions"."description" as condition
FROM conditions
LEFT JOIN patients
  ON "conditions"."patient" = "patients"."id"
LIMIT 5
```

## How it Works

1.  **Asset Identification**: The builder identifies all the unique tables (assets) required to satisfy the `fields` in your spec.
2.  **Graph Traversal**: It views your semantic layer as a graph where tables are nodes and relationships are edges.
3.  **Shortest Path Algorithm**: It finds the shortest path that connects all the required tables.
4.  **Join Clause Generation**: It translates this path into a series of `LEFT JOIN` clauses in the final SQL query.

This automated process removes the need for you to remember and write complex join logic, significantly speeding up the process of creating unified data products.
