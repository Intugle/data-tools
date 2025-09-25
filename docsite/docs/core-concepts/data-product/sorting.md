---
sidebar_position: 3
title: Sorting
---

# Sorting Results

> All examples on this and subsequent pages use the sample [healthcare dataset](https://github.com/Intugle/data-tools/tree/main/sample_data/healthcare) available in the project repository.

You can control the order of the rows in your final data product by using the `sort_by` property within the `filter` object. This allows you to sort by one or more columns in ascending or descending order.

## Single Column Sorting

To sort your data product, provide a list containing a single sort object.

### Syntax

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        # ... your fields
    ],
    "filter": {
        "sort_by": [
            {
                "id": "table_name.column_to_sort_by",
                "direction": "desc"  # or "asc"
            }
        ]
    }
}
```

-   `id`: The identifier of the column to sort by.
-   `direction`: The sort direction. Can be `asc` (ascending) or `desc` (descending). Defaults to `asc` if not specified.

### Example

This example retrieves a list of patients sorted by their healthcare expenses in descending order, showing the most expensive patients first.

```python
product_spec = {
    "name": "patients_by_expenses",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {"id": "patients.healthcare_expenses", "name": "expenses"},
    ],
    "filter": {
        "sort_by": [
            {
                "id": "patients.healthcare_expenses",
                "direction": "desc"
            }
        ],
        "limit": 5
    }
}
```

#### Generated SQL

```sql
SELECT
  "patients"."first" AS "first_name",
  "patients"."last" AS "last_name",
  "patients"."healthcare_expenses" AS "expenses"
FROM patients
ORDER BY "patients"."healthcare_expenses" DESC
LIMIT 5
```

## Sorting by an Aggregated Field

You can also sort by a calculated measure. When sorting by an aggregated field, you must provide the `alias` you defined in the `fields` list instead of the `id`.

### Syntax

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        {"id": "table.dimension", "name": "my_dimension"},
        {
            "id": "table.measure",
            "name": "my_aggregated_measure",
            "category": "measure",
            "measure_func": "sum"
        }
    ],
    "filter": {
        "sort_by": [
            {
                "alias": "my_aggregated_measure",
                "direction": "desc"
            }
        ]
    }
}
```

-   `alias`: The `name` of the measure field to sort by.

### Example

This example calculates the total healthcare expenses per city and sorts the results to show the cities with the highest total expenses first.

```python
product_spec = {
    "name": "total_healthcare_expenses_by_city",
    "fields": [
        {"id": "patients.city", "name": "city"},
        {
            "id": "patients.healthcare_expenses",
            "name": "total_expenses",
            "category": "measure",
            "measure_func": "sum",
        },
    ],
    "filter": {
        "sort_by": [
            {
                "alias": "total_expenses",
                "direction": "desc",
            }
        ],
        "limit": 5,
    },
}
```

#### Generated SQL

```sql
SELECT
  "patients"."city" as city,
  sum("patients"."healthcare_expenses") as total_expenses
FROM patients
GROUP BY
  "patients"."city"
ORDER BY
  total_expenses DESC
LIMIT 5
```
