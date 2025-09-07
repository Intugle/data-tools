<p align="center">
      <img alt="Intugle Logo" width="350" src="https://github.com/user-attachments/assets/18f4627b-af6c-4133-994b-830c30a9533b" />
 <h3 align="center"><i>The GenAI-powered toolkit for automated data intelligence.</i></h3>
</p>

[![Release](https://img.shields.io/github/release/Intugle/data-tools)](https://github.com/Intugle/data-tools/releases/tag/v0.1.0)     
[![Made with Python](https://img.shields.io/badge/Made_with-Python-blue?logo=python&logoColor=white)](https://www.python.org/)
![contributions - welcome](https://img.shields.io/badge/contributions-welcome-blue)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Open Issues](https://img.shields.io/github/issues-raw/Intugle/data-tools)](https://github.com/Intugle/data-tools/issues)
[![GitHub star chart](https://img.shields.io/github/stars/Intugle/data-tools?style=social)](https://github.com/Intugle/data-tools/stargazers)

*Automated Data Profiling, Link Prediction, and Semantic Layer Generation*

## Overview

Intugle provides a set of GenAI-powered Python tools to simplify and accelerate the journey from raw data to insights. This library empowers data and business teams to build an intelligent semantic layer over their data, enabling self-serve analytics and natural language queries. By automating data profiling, link prediction, and SQL generation, Intugle helps you build data products faster and more efficiently than traditional methods.

## Who is this for?

This tool is designed for both **data teams** and **business teams**.

*   **Data teams** can use it to automate data profiling, schema discovery, and documentation, significantly accelerating their workflow.
*   **Business teams** can use it to gain a better understanding of their data and to perform self-service analytics without needing to write complex SQL queries.

## Features

*   **Automated Data Profiling:** Generate detailed statistics for each column in your dataset, including distinct count, uniqueness, completeness, and more.
*   **Datatype Identification:** Automatically identify the data type of each column (e.g., integer, string, datetime).
*   **Key Identification:** Identify potential primary keys in your tables.
*   **LLM-Powered Link Prediction:** Use GenAI to automatically discover relationships (foreign keys) between tables.
*   **Business Glossary Generation:** Generate a business glossary for each column, with support for industry-specific domains.
*   **Semantic Layer Generation:** Create YAML files that defines your semantic layer, including models (tables) and their relationships.
*   **Data Product Creation:** Generate data products from the semantic layer, allowing you to query your data using business-friendly terms.

## Getting Started

### Installation

```bash
pip install intugle
```

### Configuration

Before running the project, you need to configure a LLM. This is used for tasks like generating business glossaries and predicting links between tables.

You can configure the LLM by setting the following environment variables:

*   `LLM_PROVIDER`: The LLM provider and model to use (e.g., `openai:gpt-3.5-turbo`) following LangChain's [conventions](https://python.langchain.com/docs/integrations/chat/)
*   `OPENAI_API_KEY`: Your API key for the LLM provider.

Here's an example of how to set these variables in your environment:

```bash
export LLM_PROVIDER="openai:gpt-3.5-turbo"
export OPENAI_API_KEY="your-openai-api-key"
```

## Quickstart

For a detailed, hands-on introduction to the project, please see the [`quickstart.ipynb`](quickstart.ipynb) notebook. It will walk you through the entire process of building a semantic layer, including:

*   **Building a Knowledge Base:** Use the `KnowledgeBuilder` to automatically profile your data, generate a business glossary, and predict links between tables.
*   **Accessing Enriched Metadata:** Learn how to access the profiling results and business glossary for each dataset.
*   **Visualizing Relationships:** Visualize the predicted links between your tables.
*   **Generating Data Products:** Use the semantic layer to generate data products and retrieve data.
*   **Serving the Semantic Layer:** Learn how to start the MCP server to interact with your semantic layer using natural language.

## Usage

The core workflow of the project involves using the `KnowledgeBuilder` to build a semantic layer, and then using the `DataProductBuilder` to generate data products from that layer.

```python
from intugle import KnowledgeBuilder, DataProductBuilder

# Define your datasets
datasets = {
    "allergies": {"path": "path/to/allergies.csv", "type": "csv"},
    "patients": {"path": "path/to/patients.csv", "type": "csv"},
    # ... add other datasets
}

# Build the knowledge base
kb = KnowledgeBuilder(datasets, domain="Healthcare")
kb.build()

# Create a DataProductBuilder
dp_builder = DataProductBuilder()

# Define an ETL model
etl = {
    "name": "patient_allergies",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {"id": "allergies.description", "name": "allergy"},
    ],
}

# Generate the data product
data_product = dp_builder.build(etl)

# View the data product as a DataFrame
print(data_product.to_df())
```

For detailed code examples and a complete walkthrough, please refer to the [`quickstart.ipynb`](quickstart.ipynb) notebook.

### MCP Server

This tool also includes an MCP server that exposes your semantic layer as a set of tools that can be used by an LLM client. This enables you to interact with your semantic layer using natural language to generate SQL queries, discover data, and more.

To start the MCP server, run the following command:

```bash
intugle-mcp
```

You can then connect to the server from any MCP client, such as Claude Desktop or Gemini CLI, at `http://localhost:8000/semantic_layer/mcp`.

## Contributing

Contributions are welcome! Please see the [`CONTRIBUTING.md`](CONTRIBUTING.md) file for guidelines.

## License

This project is licensed under the Apache License, Version 2.0. See the [`LICENSE`](LICENSE) file for details.