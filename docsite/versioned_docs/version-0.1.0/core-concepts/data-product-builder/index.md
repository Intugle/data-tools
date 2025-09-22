---
sidebar_position: 1
title: Overview
---

# Data Product Builder

The `DataProductBuilder` is the component that activates your semantic layer, turning it into a powerful engine for creating unified data products. It acts as the bridge between a high-level data request and a tangible, queryable `DataSet` object.

While the `KnowledgeBuilder` is used to *create* the semantic intelligence, the `DataProductBuilder` is used to *consume* it.

## Overview

The primary role of the `DataProductBuilder` is to abstract away the complexity of writing SQL queries across multiple tables. It takes a declarative **product specification** as input, which specifies what data you need, and leverages the manifest (the semantic layer) to figure out how to get it.

Its key responsibilities are:

1.  **Loading the Semantic Layer**: It automatically loads the entire manifest, including all sources, table schemas, and predicted relationships from your project's `.yml` files.
2.  **Interpreting the Product Specification**: It parses your request, understanding which fields you need, how to aggregate them, and how to filter or sort the final result.
3.  **Smart Query Generation**: It uses an internal `SmartQueryGenerator` to determine the most efficient join paths between the required tables and constructs the final SQL query.
4.  **Execution and Delivery**: It executes the generated query and wraps the result in a `DataSet` object, ready for analysis or use in downstream applications.

## The Product Specification

The primary input for the `DataProductBuilder` is a product specification, which you define as a Python dictionary. This model declaratively defines the structure of your desired data product.

## Usage Example

Using the `DataProductBuilder` is straightforward. Once the `KnowledgeBuilder` has successfully built the semantic layer, you can immediately start creating data products.

```python
from intugle import DataProductBuilder

# 1. Define the product specification for your data product
product_spec = {
  "name": "top_patients_by_claim_count",
  "fields": [
    {
      "id": "patients.first",
      "name": "first_name",
    },
    {
      "id": "patients.last",
      "name": "last_name",
    },
    {
      "id": "claims.id",
      "name": "number_of_claims",
      "category": "measure",
      "measure_func": "count"
    }
  ],
  "filter": {
    "sort_by": [
      {
        "id": "claims.id",
        "alias": "number_of_claims",
        "direction": "desc"
      }
    ],
    "limit": 10
  }
}

# 2. Initialize the DataProductBuilder
# It automatically loads the manifest from the current directory
dp_builder = DataProductBuilder()

# 3. Build the data product
data_product = dp_builder.build(product_spec)

# 4. Access the results
# View the data as a Pandas DataFrame
print(data_product.to_df())

# You can also inspect the generated SQL query
print(data_product.sql_query)
```

This workflow allows you to rapidly prototype and generate complex, unified datasets by simply describing what you need, letting the `DataProductBuilder` handle the underlying SQL complexity.

For a detailed breakdown of all capabilities with more examples, please see the following pages:

*   **[Basic Operations](./basic-operations.md)**: Learn how to select, alias, and limit fields.
*   **[Sorting](./sorting.md)**: See how to order your data products.
*   **[Filtering](./filtering.md)**: Explore various methods for filtering data, including selections and wildcards.
*   **[Aggregations](./aggregations.md)**: Understand how to perform grouping and aggregation functions like `COUNT` and `SUM`.
*   **[Joins](./joins.md)**: Discover how the builder automatically handles joins between tables.
*   **[Advanced Examples](./advanced-examples.md)**: See how to combine these concepts to build complex data products.
