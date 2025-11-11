<p align="center">
      <img alt="Intugle Logo" width="350" src="https://github.com/user-attachments/assets/18f4627b-af6c-4133-994b-830c30a9533b" />
 <h3 align="center"><i>The GenAI-powered toolkit for automated data intelligence.</i></h3>
</p>

<p align="center">
    <a href="https://pepy.tech/projects/intugle">
        <img alt="PyPI Downloads" src="https://static.pepy.tech/personalized-badge/intugle?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BRIGHTGREEN&left_text=downloads">
    </a>
    <img alt="Release" src="https://img.shields.io/github/release/Intugle/data-tools">
    <a href="https://www.python.org/">
        <img alt="Made with Python" src="https://img.shields.io/badge/Made_with-Python-blue?logo=python&logoColor=white">
    </a>
    <a href="https://github.com/Intugle/data-tools/blob/main/CONTRIBUTING.md">
          <img alt="contributions - welcome" src="https://img.shields.io/badge/contributions-welcome-blue">
    </a>
    <a href="https://opensource.org/licenses/Apache-2.0">
        <img alt="License: Apache 2.0" src="https://img.shields.io/badge/License-Apache_2.0-blue.svg">
    </a>
    <a href="https://github.com/Intugle/data-tools/issues">
        <img alt="Open Issues" src="https://img.shields.io/github/issues-raw/Intugle/data-tools">
    </a>
    <!-- <a href="https://github.com/Intugle/data-tools/stargazers">
        <img alt="GitHub star chart" src="https://img.shields.io/github/stars/Intugle/data-tools?style=social">
    </a> -->
</p>

*Transform Fragmented Data into Connected Semantic Data Model*

## Overview

Intugle’s GenAI-powered open-source Python library builds a semantic data model over your existing data systems. At its core, it discovers meaningful links and relationships across data assets — enriching them with profiles, classifications, and business glossaries. With this connected knowledge layer, you can enable semantic search and auto-generate queries to create unified data products, making data integration and exploration faster, more accurate, and far less manual.

## Who is this for?

*   **Data Engineers & Architects** often spend weeks manually profiling, classifying, and stitching together fragmented data assets. With Intugle, they can automate this process end-to-end, uncovering meaningful links and relationships to instantly generate a connected semantic layer.
*   **Data Analysts & Scientists** spend endless hours on data readiness and preparation before they can even start the real analysis. Intugle accelerates this by providing contextual intelligence, automatically generating SQL and reusable data products enriched with relationships and business meaning.
*   **Business Analysts & Decision Makers** are slowed down by constant dependence on technical teams for answers. Intugle removes this bottleneck by enabling natural language queries and semantic search, giving them trusted insights on demand.

## Features

*   **Semantic Data Model -** Transform raw, fragmented datasets into an intelligent semantic graph that captures entities, relationships, and context — the foundation for connected intelligence.
*   **Business Glossary & Semantic Search:** Auto-generate a business glossary and enable search that understands meaning, not just keywords — making data more accessible across technical and business users.
*   **Data Products -** Instantly generate SQL and reusable data products enriched with context, eliminating manual pipelines and accelerating data-to-insight.
*   **Conceptual Search -** Generate data product plans from natural language queries, bridging the gap between business questions and executable data product definitions. Learn more in the [documentation](https://intugle.github.io/data-tools/docs/core-concepts/data-product/conceptual-search).


## Getting Started

### Installation

For Windows and Linux, you can follow these steps. For macOS, please see the additional steps in the macOS section below.

Before installing, it is recommended to create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Then, install the package:

```bash
pip install intugle
```

#### macOS

For macOS users, you may need to install the `libomp` library:

```bash
brew install libomp
```

If you installed Python using the official installer from python.org, you may also need to install SSL certificates by running the following command in your terminal. Please replace `3.XX` with your specific Python version. This step is not necessary if you installed Python using Homebrew.

```bash
/Applications/Python\ 3.XX/Install\ Certificates.command
```

### Configuration

Before running the project, you need to configure a LLM. This is used for tasks like generating business glossaries and predicting links between tables.

You can configure the LLM by setting the following environment variables:

*   `LLM_PROVIDER`: The LLM provider and model to use (e.g., `openai:gpt-3.5-turbo`) following LangChain's [conventions](https://python.langchain.com/docs/integrations/chat/)
*   `API_KEY`: Your API key for the LLM provider. The exact name of the variable may vary from provider to provider.

Here's an example of how to set these variables in your environment:

```bash
export LLM_PROVIDER="openai:gpt-3.5-turbo"
export OPENAI_API_KEY="your-openai-api-key"
```

## Quickstart

For a detailed, hands-on introduction to the project, please see our quickstart notebooks:

| Domain                  | Notebook                                                                                                             | Open in Colab                                                                                                                                                           |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Healthcare**          | [`quickstart_healthcare.ipynb`](notebooks/quickstart_healthcare.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_healthcare.ipynb) |
| **Tech Manufacturing**  | [`quickstart_tech_manufacturing.ipynb`](notebooks/quickstart_tech_manufacturing.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_tech_manufacturing.ipynb) |
| **FMCG**                | [`quickstart_fmcg.ipynb`](notebooks/quickstart_fmcg.ipynb)             | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_fmcg.ipynb)             |
| **Sports Media**        | [`quickstart_sports_media.ipynb`](notebooks/quickstart_sports_media.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_sports_media.ipynb) |
| **Databricks Unity Catalog [Health Care]** | [`quickstart_healthcare_databricks.ipynb`](notebooks/quickstart_healthcare_databricks.ipynb) | Databricks Notebook Only |
| **Snowflake Horizon Catalog [ FMCG ]** | [`quickstart_fmcg_snowflake.ipynb`](notebooks/quickstart_fmcg_snowflake.ipynb) | Snowflake Notebook Only |
| **Native Snowflake with Cortex Analyst [ Tech Manufacturing ]** | [`quickstart_native_snowflake.ipynb`](notebooks/quickstart_native_snowflake.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_native_snowflake.ipynb) |
| **Native Databricks with AI/BI Genie [ Tech Manufacturing ]** | [`quickstart_native_databricks.ipynb`](notebooks/quickstart_native_databricks.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_native_databricks.ipynb) |
| **Streamlit App**       | [`quickstart_streamlit.ipynb`](notebooks/quickstart_streamlit.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_streamlit.ipynb) |
| **Conceptual Search**   | [`quickstart_conceptual_search.ipynb`](notebooks/quickstart_conceptual_search.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_conceptual_search.ipynb) |
These datasets will take you through the following steps:

*   **Generate Semantic Model** → The unified layer that transforms fragmented datasets, creating the foundation for connected intelligence.
    *   **1.1 Profile and classify data** → Analyze your data sources to understand their structure, data types, and other characteristics.
    *   **1.2 Discover links & relationships among data** → Reveal meaningful connections (PK & FK) across fragmented tables.
    *   **1.3 Generate a business glossary** → Create business-friendly terms and use them to query data with context.
    *   **1.4 Enable semantic search** → Intelligent search that understands meaning, not just keywords—making data more accessible across both technical and business users.
    *   **1.5 Visualize semantic model**→ Get access to enriched metadata of the semantic layer in the form of YAML files and visualize in the form of graph
*   **Build Unified Data Products** → Simply pick the attributes across your data tables, and let the toolkit auto-generate queries with all the required joins, transformations, and aggregations using the semantic layer. When executed, these queries produce reusable data products.

## Documentation

For more detailed information, advanced usage, and tutorials, please refer to our full [documentation site](https://intugle.github.io/data-tools/).

## Usage

The core workflow of the project involves using the `SemanticModel` to build a semantic layer, and then using the `DataProduct` to generate data products from that layer.

```python
from intugle import SemanticModel

# Define your datasets
datasets = {
    "allergies": {"path": "path/to/allergies.csv", "type": "csv"},
    "patients": {"path": "path/to/patients.csv", "type": "csv"},
    "claims": {"path": "path/to/claims.csv", "type": "csv"},
    # ... add other datasets
}

# Build the semantic model
sm = SemanticModel(datasets, domain="Healthcare")
sm.build()

# Access the profiling results
print(sm.profiling_df.head())

# Access the discovered links
print(sm.links_df)
```
For detailed code examples and a complete walkthrough, please see our [quickstart notebooks](#quickstart).

### Data Product

Once the semantic model is built, you can use the `DataProduct` class to generate unified data products from the semantic layer.

```python
from intugle import DataProduct

# Define an ETL model
etl = {
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

# Create a DataProduct and build it
dp = DataProduct()
data_product = dp.build(etl)

# View the data product as a DataFrame
print(data_product.to_df())
```

### Semantic Search

The semantic search feature allows you to search for columns in your datasets using natural language. It is built on top of the [Qdrant](https://qdrant.tech/) vector database.

#### Prerequisites

To use the semantic search feature, you need to have a running Qdrant instance. You can start one using the following Docker command:

```bash
docker run -d -p 6333:6333 -p 6334:6334 \
    -v qdrant_storage:/qdrant/storage:z \
    --name qdrant qdrant/qdrant
```

You also need to configure the Qdrant URL and API key (if using authorization) in your environment variables:

```bash
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your-qdrant-api-key" # if authorization is used
```

Currently, the semantic search feature only supports OpenAI embedding models. Therefore, you need to have an OpenAI API key set up in your environment. The default model is `text-embedding-ada-002`. You can change the embedding model by setting the `EMBEDDING_MODEL_NAME` environment variable.

**For OpenAI models:**

```bash
export OPENAI_API_KEY="your-openai-api-key"
export EMBEDDING_MODEL_NAME="openai:ada"
```

**For Azure OpenAI models:**

```bash
export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
export AZURE_OPENAI_ENDPOINT="your-azure-openai-endpoint"
export OPENAI_API_VERSION="your-openai-api-version"
export EMBEDDING_MODEL_NAME="azure_openai:ada"
```

#### Usage

Once you have built the semantic model, you can use the `search` method to perform a semantic search. The search function returns a pandas DataFrame containing the search results, including the column\'s profiling metrics, category, table name, and table glossary.

```python
from intugle import SemanticModel

# Define your datasets
datasets = {
    "allergies": {"path": "path/to/allergies.csv", "type": "csv"},
    "patients": {"path": "path/to/patients.csv", "type": "csv"},
    "claims": {"path": "path/to/claims.csv", "type": "csv"},
    # ... add other datasets
}

# Build the semantic model
sm = SemanticModel(datasets, domain="Healthcare")
sm.build()
# Perform a semantic search
search_results = sm.search("reason for hospital visit")

# View the search results
print(search_results)
```
For detailed code examples and a complete walkthrough, please see our [quickstart notebooks](#quickstart).

### MCP Server

Intugle includes a built-in MCP (Model Context Protocol) server that exposes your semantic layer to AI assistants and LLM-powered clients. Its main purpose is to allow agents to understand your data's structure by using tools like `get_tables` and `get_schema`.

Once your semantic model is built, you can start the server with a simple command:

```bash
intugle-mcp
```

This enables AI agents to programmatically interact with your data context. This also enables vibe coding with the library

For detailed instructions on setting up the server and connecting your favorite client, please see our full [documentation](https://intugle.github.io/data-tools/docs/mcp-server).

<!-- mcp-name: io.github.intugle/intugle-vibe-mcp -->

### Streamlit App

The `intugle` library includes a Streamlit application that provides an interactive web interface for building and visualizing semantic data models.

To use the Streamlit app, install `intugle` with the `streamlit` extra:

```bash
pip install intugle[streamlit]
```

You can launch the Streamlit application using the `intugle-mcp` command or `uvx`:

```bash
intugle-streamlit
# Or using uvx
uvx --from intugle[streamlit] intugle-streamlit
```

Open the URL provided in your terminal (usually `http://localhost:8501`) to access the application. For more details, refer to the [Streamlit App documentation](https://intugle.github.io/data-tools/docs/streamlit-app).

To run the app in a cloud environment like Google Colab, please refer to our [Streamlit quickstart notebook](notebooks/quickstart_streamlit.ipynb).

## Community

Join our community to ask questions, share your projects, and connect with other users.

<!-- *   [Join our Slack](https://join.slack.com/share/enQtOTQ4NDc1MzYzOTg2MC02OTc2MTU1Njg3NDEyZjQwN2IzMzEwMjc5NmU4MjhiZmJlMDdiMzMzYjI5YWJiNDhkYWM4ODU0MGY4NTUyNjhi) -->
*   [Join our Discord](https://discord.gg/NqR9tNWVTm)


## Contributing

Contributions are welcome! Please see the [`CONTRIBUTING.md`](CONTRIBUTING.md) file for guidelines.

## License

This project is licensed under the Apache License, Version 2.0. See the [`LICENSE`](LICENSE) file for details.
