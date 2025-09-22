---
sidebar_position: 5
title: Aggregations
---

# Aggregations

> All examples on this and subsequent pages use the sample [healthcare dataset](https://github.com/Intugle/data-tools/tree/main/sample_data/healthcare) available in the project repository.

Aggregations allow you to perform calculations on groups of rows to derive summary insights. This is equivalent to using `GROUP BY` in SQL. The `DataProductBuilder` automatically applies grouping when you mix dimensions and measures in your `fields` list.

## Dimensions and Measures

-   **Dimension**: A categorical column that you want to group by (e.g., `city`, `gender`, `product_category`). In the `fields` list, this is the default `category`.
-   **Measure**: A calculation performed on the data within each group (e.g., a count of rows, a sum of expenses). To define a measure, you must set the `category` to `"measure"` and specify a `measure_func`.

## Performing a `COUNT`

Counting is one of the most common aggregations. It counts the number of rows within each dimension group.

### Syntax

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        {"id": "table.dimension_column", "name": "my_dimension"},
        {
            "id": "table.column_to_count",
            "name": "my_count",
            "category": "measure",
            "measure_func": "count"
        }
    ],
}
```

-   `category`: Must be set to `"measure"`.
-   `measure_func`: The aggregation function to apply. For counting, use `"count"`.

### Example

This example counts the number of claims for each patient.

```python
product_spec = {
    "name": "patient_claim_counts",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {
            "id": "claims.id",
            "name": "number_of_claims",
            "category": "measure",
            "measure_func": "count",
        },
    ],
    "filter": {"limit": 5}
}
```

#### Generated SQL

```sql
SELECT
  "patients"."first" as first_name,
  "patients"."last" as last_name,
  count("claims"."id") as number_of_claims
FROM claims
LEFT JOIN patients
  ON "claims"."patientid" = "patients"."id"
GROUP BY
  "patients"."first",
  "patients"."last"
LIMIT 5
```

## Performing a `SUM`

You can also perform mathematical calculations like `SUM`, `AVG`, `MIN`, and `MAX`.

### Syntax

```python
product_spec = {
    "name": "your_product_name",
    "fields": [
        {"id": "table.dimension_column", "name": "my_dimension"},
        {
            "id": "table.numeric_column_to_sum",
            "name": "my_sum",
            "category": "measure",
            "measure_func": "sum"
        }
    ],
}
```

-   `measure_func`: Can be `"sum"`, `"average"`, `"max"`, etc.

### Example

This example calculates the total healthcare expenses for patients, grouped by city.

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
    "filter": {"limit": 5}
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
LIMIT 5
```

## Using Date Functions as Dimensions

You can also group by derived values, such as the year or month from a date column, by using the `dimension_func`.

### Example

This example counts the number of claims per year.

```python
product_spec = {
    "name": "claims_by_year",
    "fields": [
        {
            "id": "claims.servicedate",
            "name": "service_year",
            "dimension_func": "year",
        },
        {
            "id": "claims.id",
            "name": "number_of_claims",
            "category": "measure",
            "measure_func": "count",
        },
    ],
    "filter": {"limit": 5}
}
```

#### Generated SQL

```sql
SELECT
  year("claims"."servicedate") as service_year,
  count("claims"."id") as number_of_claims
FROM claims
GROUP BY
  service_year
LIMIT 5
```
