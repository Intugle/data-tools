---
sidebar_position: 7
title: Advanced Examples
---

# Advanced Examples

> All examples on this and subsequent pages use the sample [healthcare dataset](https-://github.com/Intugle/data-tools/tree/main/sample_data/healthcare) available in the project repository.

By combining the concepts from the previous pages—such as aliasing, filtering, aggregations, and joins—you can build sophisticated data products to answer complex business questions. This page provides examples of how to combine these operations.

## Combining Multiple Filters

You can apply multiple filter criteria by adding more objects to the `selections` and `wildcards` lists. By default, all conditions are combined with an `AND` operator.

### Example

This example finds male patients who live in Boston. It applies two separate `selections` filters: one for `city` and one for `gender`.

```python
product_spec = {
    "name": "male_patients_in_boston",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {"id": "patients.city", "name": "city"},
        {"id": "patients.gender", "name": "gender"},
    ],
    "filter": {
        "selections": [
            {"id": "patients.city", "values": ["Boston"]},
            {"id": "patients.gender", "values": ["M"]},
        ],
        "limit": 10,
    },
}
```

#### Generated SQL

```sql
SELECT
  "patients"."first" as first_name,
  "patients"."last" as last_name,
  "patients"."city" as city,
  "patients"."gender" as gender
FROM patients
WHERE ("patients"."city" IN ('Boston',))
  AND ("patients"."gender" IN ('M',))
LIMIT 10
```

## Joining and Filtering Across Tables

The real power of the `DataProductBuilder` becomes apparent when you combine joins with filters that span multiple tables.

### Example

This example answers a complex question: "Show me the names of patients from Boston who have been diagnosed with a condition containing the word 'fracture'."

To do this, it:
1.  **Selects** fields from both `patients` and `conditions`, triggering an implicit join.
2.  **Filters** on `patients.city` using a `selection`.
3.  **Filters** on `conditions.description` using a `wildcard`.

```python
product_spec = {
    "name": "conditions_of_boston_patients",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {"id": "conditions.description", "name": "condition"},
    ],
    "filter": {
        "selections": [
            {"id": "patients.city", "values": ["Boston"]},
        ],
        "wildcards": [
            {
                "id": "conditions.description",
                "value": "fracture",
                "option": "contains",
            }
        ],
        "limit": 10,
    },
}
```

#### Generated SQL

The builder correctly joins the tables and applies both `WHERE` clauses.

```sql
SELECT
  "patients"."first" as first_name,
  "patients"."last" as last_name,
  "conditions"."description" as condition
FROM conditions
LEFT JOIN patients
  ON "conditions"."patient" = "patients"."id"
WHERE ("patients"."city" IN ('Boston',))
  AND "conditions"."description" LIKE '%fracture%'
LIMIT 10
```
