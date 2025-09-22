---
sidebar_position: 5
title: Semantic Search
---

# Semantic Search

Semantic search transforms how you find and explore your data. Instead of relying on exact keyword matches, it allows you to search your entire connected data landscape using natural language. This feature understands the *meaning* and *context* behind your query, making it possible to discover relevant data assets even if you don't know their exact names or technical details.

## How it works

The semantic search capability is built on a foundation of vector embeddings and a specialized vector database. Here’s a high-level overview of the process:

1.  **Indexing**: After the `SemanticModel` profiles your data and generates a business glossary, it creates meaningful text from your metadata (column names, descriptions, and tags).
2.  **Vectorization**: This text is then converted into numerical representations—called vector embeddings—using a sophisticated embedding model. These embeddings capture the semantic meaning of the metadata.
3.  **Storage**: The generated embeddings are stored in a **Qdrant** vector database, creating an indexed, searchable knowledge base of all your columns.
4.  **Querying**: When you perform a search, your natural language query is also converted into a vector embedding.
5.  **Similarity Search**: The system then searches the Qdrant database for the vectors that are most similar to your query's vector. The columns corresponding to these vectors are returned as the most relevant results.

### Hybrid search for better results

To deliver highly accurate results, the library employs a hybrid search strategy that combines two different embedding techniques:

*   **Dense Embeddings**: This technique creates a single, compact vector to represent the meaning of a piece of text. It is highly effective for short, concise text like **column names** and **tags**.
*   **Late-Fusion Embeddings**: This advanced technique tokenizes longer text (like a **business glossary description**), embeds each token individually, and then compares them. This method is better at capturing the nuanced meaning within longer descriptions.

By running these searches in parallel and intelligently combining their results, the system provides more relevant and context-aware matches than a single embedding strategy could alone.

## Prerequisites

To use the semantic search feature, you must have a running Qdrant instance and provide API credentials for an embedding model.

### 1. Run Qdrant

You can start a Qdrant instance using the following Docker command:

```bash
docker run -d -p 6333:6333 -p 6334:6334 \
    -v qdrant_storage:/qdrant/storage:z \
    --name qdrant qdrant/qdrant
```

### 2. Configure environment variables

Next, you need to configure the necessary environment variables. Currently, only OpenAI embedding models are supported.

```bash
# The URL of your running Qdrant instance
export QDRANT_URL="http://localhost:6333"

# Your Qdrant API key (only if you have enabled authorization)
export QDRANT_API_KEY="your-qdrant-api-key"

# The embedding model to use (the default is openai:ada)
export EMBEDDING_MODEL_NAME="openai:ada"

# Your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key"
```

If you are using Azure OpenAI, you will need to set these variables instead:

```bash
export EMBEDDING_MODEL_NAME="azure_openai:ada"
export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
export AZURE_OPENAI_ENDPOINT="your-azure-openai-endpoint"
export OPENAI_API_VERSION="your-openai-api-version"
```

## Usage with SemanticModel

The simplest way to use semantic search is through the `SemanticModel` after the semantic model has been built.

The `sm.build()` method generates all the rich metadata that the search engine needs. The first time you run `sm.search()`, this metadata is automatically vectorized and indexed in your Qdrant instance.

```python
from intugle import SemanticModel

# Define your datasets
datasets = {
    "allergies": {"path": "path/to/allergies.csv", "type": "csv"},
    "patients": {"path": "path/to/patients.csv", "type": "csv"},
    # ... add other datasets
}

# Initialize and build the semantic model
sm = SemanticModel(datasets, domain="Healthcare")
sm.build()

# Perform a semantic search
search_results = sm.search("reason for hospital visit")

# View the search results
print(search_results)
```

## Standalone Usage

For more granular control, you can use the `SemanticSearch` class directly. This is useful if you want to build or query the search index without running the entire `SemanticModel` pipeline, assuming the metadata `.yml` files already exist.

```python
from intugle.semantic_search import SemanticSearch

# This assumes your project's .yml files are in the default location.
# You can also specify the path to your models directory:
# search_client = SemanticSearch(project_base="/path/to/your/models")
search_client = SemanticSearch()

# 1. Initialize the search index.
# This reads the .yml files, vectorizes the metadata, and populates Qdrant.
# You only need to run this once, or whenever your source metadata changes.
print("Initializing semantic search index...")
search_client.initialize()
print("Initialization complete.")

# 2. Perform a search.
query = "reason for hospital visit"
search_results = search_client.search(query)

# View the results
print(search_results)
```

## Understanding the results

The `search()` method returns a **Pandas DataFrame** containing the most relevant columns, sorted by their relevance score. The DataFrame includes the following key information:

*   `column_id`: A unique identifier for the column (`table_name.column_name`).
*   `score`: The similarity score (between 0 and 1) indicating how relevant the column is to the query.
*   `relevancy`: A human-readable category (`most-relevant`, `relevant`, `less-relevant`) based on the score.
*   `column_name`: The name of the matched column.
*   `column_glossary`: The auto-generated business glossary for the column.
*   `table_name`: The name of the table the column belongs to.
*   `uniqueness`: The uniqueness score of the column's data.
*   `completeness`: The completeness score of the column's data.

This rich output not only helps you find the right data but also gives you immediate context about its quality and business meaning.
