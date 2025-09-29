---
sidebar_position: 1
---

:::info

The following modules have been renamed in this version:
- KnowledgeBuilder -> SemanticModel
- DataProductBuilder -> DataProduct

:::

# Core concepts

This section dives deep into the fundamental components and architectural ideas that power the Intugle Data Tools library.

Understanding these concepts is key to using the library effectively and leveraging its full potential for automating data intelligence.

### Key Components

*   **Semantic Intelligence**: This is the core engine that automatically analyzes, enriches, and connects your raw data. It's composed of several key parts:
    *   **`SemanticModel`**: The main orchestrator that runs the entire intelligence pipeline.
    *   **`DataSet`**: A container for a single data source, holding both the raw data and all the metadata generated about it.
    *   **Link Prediction**: The process that automatically discovers meaningful relationships and potential join keys between different datasets.
    *   **Semantic Search**: The capability that allows you to find data using natural language queries.
*   **Data Product**: This component uses the semantic layer to build unified, queryable datasets. You define *what* data you need, and the `DataProduct` automatically generates the complex SQL to retrieve it.