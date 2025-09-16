---
sidebar_position: 2
title: Basic Operations
---

# Basic Operations

This page covers the fundamental operations for creating a data product: selecting columns, renaming them (aliasing), and limiting the number of results.

> All examples on this and subsequent pages use the sample [healthcare dataset](https-://github.com/Intugle/data-tools/tree/main/sample_data/healthcare) available in the project repository.

## Selecting Fields

The most basic action is to select the columns you want in your data product. You do this by defining a list of `fields`.

### Syntax

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        {"id": "table_name.column_name_1"},
        {"id": "table_name.column_name_2"},
        # ... more fields
    ],
}
```

-   `id`: The unique identifier for the column, formatted as `table_name.column_name`.

### Example

This example creates a simple data product with three columns from the `patients` table.

```python
product_spec = {
    "name": "patient_contact_info",
    "fields": [
        {"id": "patients.first"},
        {"id": "patients.last"},
        {"id": "patients.ssn"},
    ],
}
```

#### Generated SQL

```sql
SELECT
  "patients"."first",
  "patients"."last",
  "patients"."ssn"
FROM patients
```

## Aliasing Fields

It's often useful to rename columns in your final data product to be more descriptive or to avoid naming conflicts. You can do this by adding the `name` key to a field's definition.

### Syntax

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        {
            "id": "table_name.column_name",
            "name": "your_new_column_name"
        },
    ],
}
```

-   `name`: The desired alias for the column in the output.

### Example

This example selects patient information and renames the columns for clarity.

```python
product_spec = {
    "name": "patient_demographics",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {"id": "patients.marital", "name": "marital_status"},
    ],
}
```

#### Generated SQL

```sql
SELECT
  "patients"."first" AS "first_name",
  "patients"."last" AS "last_name",
  "patients"."marital" AS "marital_status"
FROM patients
```

## Limiting Results

To control the size of your output, you can use the `limit` property within the `filter` object. This is useful for previewing data or retrieving a top-N list.

### Syntax

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        # ... your fields
    ],
    "filter": {
        "limit": 10  # The number of rows to return
    }
}
```

-   `limit`: The maximum number of rows to return.

### Example

This example retrieves the first 5 records from the `patients` table.

```python
product_spec = {
    "name": "first_five_patients",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
    ],
    "filter": {
        "limit": 5
    }
}
```

#### Generated SQL

```sql
SELECT
  "patients"."first" AS "first_name",
  "patients"."last" AS "last_name"
FROM patients
LIMIT 5
```

#### Resulting DataFrame

| | first_name | last_name |
|---:|:---|:---|
| 0 | Damon455 | Langosh790 |
| 1 | Thi53 | Wunsch504 |
| 2 | Phillis443 | Walter473 |
| 3 | Jerrold404 | Herzog843 |
| 4 | Brandon214 | Watsica258 |
