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

*Transform Fragmented Data into Connected Semantic Layer*

## Overview

Intugle’s GenAI-powered open-source Python library builds an intelligent semantic layer over your existing data systems. At its core, it discovers meaningful links and relationships across data assets — enriching them with profiles, classifications, and business glossaries. With this connected knowledge layer, you can enable semantic search and auto-generate queries to create unified data products, making data integration and exploration faster, more accurate, and far less manual.

## Who is this for?

*   **Data Engineers & Architects** often spend weeks manually profiling, classifying, and stitching together fragmented data assets. With Intugle, they can automate this process end-to-end, uncovering meaningful links and relationships to instantly generate a connected semantic layer.
*   **Data Analysts & Scientists** spend endless hours on data readiness and preparation before they can even start the real analysis. Intugle accelerates this by providing contextual intelligence, automatically generating SQL and reusable data products enriched with relationships and business meaning.
*   **Business Analysts & Decision Makers** are slowed down by constant dependence on technical teams for answers. Intugle removes this bottleneck by enabling natural language queries and semantic search, giving them trusted insights on demand.

## Features

*   **Semantic Intelligence:** Transform raw, fragmented datasets into an intelligent semantic graph that captures entities, relationships, and context — the foundation for connected intelligence.
*   **Business Glossary & Semantic Search:** Auto-generate a business glossary and enable search that understands meaning, not just keywords — making data more accessible across technical and business users.
*   **Smart SQL & Data Products:** Instantly generate SQL and reusable data products enriched with context, eliminating manual pipelines and accelerating data-to-insight.

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
| **Tech Manufacturing**  | [`quickstart_tech_company.ipynb`](notebooks/quickstart_tech_company.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_tech_company.ipynb) |
| **FMCG**                | [`quickstart_fmcg.ipynb`](notebooks/quickstart_fmcg.ipynb)             | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_fmcg.ipynb)             |
| **Sports Media**        | [`quickstart_sports_media.ipynb`](notebooks/quickstart_sports_media.ipynb) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Intugle/data-tools/blob/main/notebooks/quickstart_sports_media.ipynb) |
| **Databricks Unity Catalog [Health Care]** | [`quickstart_healthcare_databricks.ipynb`](notebooks/quickstart_healthcare_databricks.ipynb) | Databricks Notebook Only |

These datasets will take you through the following steps:

*   **Building a Knowledge Base:** Use the `KnowledgeBuilder` to automatically profile your data, generate a business glossary, and predict links between tables.
*   **Accessing Enriched Metadata:** Learn how to access the profiling results and business glossary for each dataset.
*   **Visualizing Relationships:** Visualize the predicted links between your tables.
*   **Generating Data Products:** Use the semantic layer to generate data products and retrieve data.
*   **Searching the Knowledge Base:** Use semantic search to find relevant columns in your datasets using natural language.

## Documentation

For more detailed information, advanced usage, and tutorials, please refer to our full [documentation site](https://intugle.github.io/data-tools/).

## Usage

The core workflow of the project involves using the `KnowledgeBuilder` to build a semantic layer, and then using the `DataProductBuilder` to generate data products from that layer.

```python
from intugle import KnowledgeBuilder, DataProductBuilder

# Define your datasets
datasets = {
    "allergies": {"path": "path/to/allergies.csv", "type": "csv"},
    "patients": {"path": "path/to/patients.csv", "type": "csv"},
    "claims": {"path": "path/to/claims.csv", "type": "csv"},
    # ... add other datasets
}

# Build the knowledge base
kb = KnowledgeBuilder(datasets, domain="Healthcare")
kb.build()

# Create a DataProductBuilder
dp_builder = DataProductBuilder()

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

# Generate the data product
data_product = dp_builder.build(etl)

# View the data product as a DataFrame
print(data_product.to_df())
```

For detailed code examples and a complete walkthrough, please see the quickstart notebooks under the notebooks directory.

### Semantic Search

The semantic search feature allows you to search for columns in your datasets using natural language. It is built on top of the [Qdrant](https://qdrant.tech/) vector database.

#### Prerequisites

To use the semantic search feature, you need to have a running Qdrant instance. You can start one using the following Docker command:

```bash
docker run -p 6333:6333 -p 6334:6334 \
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

Once you have built the knowledge base, you can use the `search` method to perform a semantic search. The search function returns a pandas DataFrame containing the search results, including the column\'s profiling metrics, category, table name, and table glossary.

```python
from intugle import KnowledgeBuilder

# Define your datasets
datasets = {
    "allergies": {"path": "path/to/allergies.csv", "type": "csv"},
    "patients": {"path": "path/to/patients.csv", "type": "csv"},
    "claims": {"path": "path/to/claims.csv", "type": "csv"},
    # ... add other datasets
}

# Build the knowledge base
kb = KnowledgeBuilder(datasets, domain="Healthcare")
kb.build()
# Perform a semantic search
search_results = kb.search("reason for hospital visit")

# View the search results
print(search_results)
```
For detailed code examples and a complete walkthrough, please see the quickstart notebooks under the notebooks directory.

## Community

Join our community to ask questions, share your projects, and connect with other users.

<!-- *   [Join our Slack](https://join.slack.com/share/enQtOTQ4NDc1MzYzOTg2MC02OTc2MTU1Njg3NDEyZjQwN2IzMzEwMjc5NmU4MjhiZmJlMDdiMzMzYjI5YWJiNDhkYWM4ODU0MGY4NTUyNjhi) -->
*   [Join our Discord](https://discord.gg/NqR9tNWVTm)


## Contributing

Contributions are welcome! Please see the [`CONTRIBUTING.md`](CONTRIBUTING.md) file for guidelines.

## License

This project is licensed under the Apache License, Version 2.0. See the [`LICENSE`](LICENSE) file for details.
