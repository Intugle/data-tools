---
sidebar_position: 4
title: Filtering
---

# Filtering Data

> All examples on this and subsequent pages use the sample [healthcare dataset](https://github.com/Intugle/data-tools/tree/main/sample_data/healthcare) available in the project repository.

The `filter` object is a powerful tool for narrowing down the results in your data product. You can filter data using precise matches (`selections`) or pattern-based matching (`wildcards`).

## Filtering with Selections

Selections allow you to filter for rows where a column's value is in a specific list, is `NULL`, or is not in a list.

### `IN` Clause

To include rows based on a list of possible values, use the `values` property.

#### Syntax

```python
product_spec = {
    # ...
    "filter": {
        "selections": [
            {
                "id": "table_name.column_name",
                "values": ["value1", "value2"]
            }
        ]
    }
}
```

-   `values`: A list of values to match.

#### Example

This example retrieves all patients who live in Boston or Quincy.

```python
product_spec = {
    "name": "patients_from_boston_or_quincy",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.city", "name": "city"},
    ],
    "filter": {
        "selections": [
            {
                "id": "patients.city",
                "values": ["Boston", "Quincy"],
            }
        ],
        "limit": 5,
    },
}
```

##### Generated SQL

```sql
SELECT
  "patients"."first" AS "first_name",
  "patients"."city" AS "city"
FROM patients
WHERE ("patients"."city" IN ('Boston', 'Quincy'))
LIMIT 5
```

### `NOT IN` Clause

To exclude rows based on a list of values, add `"exclude": true`.

#### Syntax

```python
product_spec = {
    # ...
    "filter": {
        "selections": [
            {
                "id": "table_name.column_name",
                "values": ["value_to_exclude"],
                "exclude": True
            }
        ]
    }
}
```

-   `exclude`: When set to `True`, this reverses the filter.

#### Example

This example retrieves all patients who do *not* live in Boston.

```python
product_spec = {
    "name": "patients_not_in_boston",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.city", "name": "city"},
    ],
    "filter": {
        "selections": [
            {
                "id": "patients.city",
                "values": ["Boston"],
                "exclude": True,
            }
        ],
        "limit": 5,
    },
}
```

##### Generated SQL

```sql
SELECT
  "patients"."first" AS "first_name",
  "patients"."city" AS "city"
FROM patients
WHERE ("patients"."city" NOT IN ('Boston',))
LIMIT 5
```

### `IS NULL` Clause

To find rows where a column has no value, use `"null": true`.

#### Syntax

```python
product_spec = {
    # ...
    "filter": {
        "selections": [
            {
                "id": "table_name.column_name",
                "null": True
            }
        ]
    }
}
```

-   `null`: When set to `True`, filters for `NULL` values.

#### Example

This example finds patients who do not have a recorded SSN.

```python
product_spec = {
    "name": "patients_with_no_ssn",
    "fields": [
        {"id": "patients.id", "name": "patient_id"},
        {"id": "patients.ssn", "name": "ssn"},
    ],
    "filter": {
        "selections": [
            {
                "id": "patients.ssn",
                "null": True,
            }
        ]
    },
}
```

##### Generated SQL

```sql
SELECT
  "patients"."id" AS "patient_id",
  "patients"."ssn" AS "ssn"
FROM patients
WHERE ("patients"."ssn" IS NULL)
```

## Filtering with Wildcards

Wildcards are used for pattern matching in text fields, which translates to a `LIKE` clause in SQL.

### Syntax

```python
product_spec = {
    # ...
    "filter": {
        "wildcards": [
            {
                "id": "table_name.column_name",
                "value": "pattern",
                "option": "contains"
            }
        ]
    }
}
```

-   `value`: The text pattern to search for.
-   `option`: The type of match. Can be:
    -   `starts_with`: `LIKE 'pattern%'`
    -   `ends_with`: `LIKE '%pattern'`
    -   `contains`: `LIKE '%pattern%'`
    -   `exactly_matches`: `LIKE 'pattern'`

### Example

This example finds all conditions that contain the word "fracture".

```python
product_spec = {
    "name": "fracture_conditions",
    "fields": [
        {"id": "conditions.description", "name": "condition_description"},
    ],
    "filter": {
        "wildcards": [
            {
                "id": "conditions.description",
                "value": "fracture",
                "option": "contains",
            }
        ],
    },
}
```

#### Generated SQL

```sql
SELECT
  "conditions"."description" AS "condition_description"
FROM conditions
WHERE "conditions"."description" LIKE '%fracture%'
```
