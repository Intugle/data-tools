---
sidebar_position: 8
title: Streamlit App
---

# Intugle - Streamlit App

This Streamlit application provides an interactive web interface for the `intugle` library. It allows users to upload their tabular data (CSV/Excel), configure a Large Language Model (LLM), and step through the process of building a semantic data model. The app profiles the data, generates a business glossary, identifies relationships between datasets, and visualizes the resulting semantic graph.

## ✨ Features

- **File Upload**: Upload multiple CSV or Excel files directly in the browser.
- **Interactive Data Prep**: Interactively rename tables and select, rename, or drop columns before processing.
- **LLM Configuration**: Securely configure and connect to your preferred LLM provider (OpenAI, Azure OpenAI, Gemini).
- **Automated Data Profiling**: Automatically calculates key metrics like uniqueness, completeness, and data types for every column.
- **AI-Powered Business Glossary**: Leverages an LLM to generate a business glossary for all tables and columns, adding crucial context.
- **Automated Link Prediction**: Discovers potential relationships (foreign keys) between your tables.
- **Interactive Visualization**: Displays the final semantic model as an interactive network graph.
- **Detailed Results**: Provides a tabular view of all predicted links with detailed metrics.
- **Export Artifacts**: Download the generated semantic model artifacts (`.yml` files) as a ZIP archive for use in other systems.

## 🚀 Getting Started

Follow these instructions to set up and run the application on your local machine.

### Prerequisites

- Python 3.10+
- `uv` (Optional: for `uvx` command)

### 1. Installation

To use the Streamlit app, install `intugle` with the `streamlit` extra:

```bash
pip install intugle[streamlit]
```

### 2. Configuration

The application requires credentials for a Large Language Model to generate the business glossary and perform other AI-powered tasks.

You can configure your LLM provider and API keys directly in the application's sidebar after launching it. The app will guide you on which credentials are required for your chosen provider (e.g., `OPENAI_API_KEY` for OpenAI).

### 3. Running the App

You can launch the Streamlit application using the `intugle-streamlit` command or `uvx`:

```bash
intugle-streamlit
# Or using uvx
uvx --from intugle[streamlit] intugle-streamlit
```

Open the URL provided in your terminal (usually `http://localhost:8501`) to access the application.

## ⚙️ How It Works

The application guides you through a simple, multi-step process, which is tracked in the sidebar:

1.  **Upload Files**: Start by uploading one or more CSV or Excel files. The app will display a summary of the uploaded tables.
2.  **Configure LLM**: In the sidebar, choose your LLM provider (OpenAI, Azure, or Gemini) and enter the necessary API keys and configuration details.
3.  **Prepare Data**: Review the uploaded tables. You can rename tables and modify columns (rename, or ignore/drop them). Once you are satisfied, click **"Freeze column names"** to lock in your changes.
4.  **Build Semantic Model**: After preparing your data, click **"Create Semantic Model"**. You will be prompted to provide a "domain" (e.g., *Healthcare*, *Manufacturing*) to give the LLM context. The app will then profile the data and generate a business glossary for each table.
5.  **Predict Links**: Once profiling is complete, click **"Run Link Prediction"** to discover the relationships between your datasets.
6.  **Explore & Download**: View the results as an interactive graph or a detailed table. You can download the underlying YAML configuration files from the sidebar at any time.

## Running on Google Colab

To run the Streamlit app in a cloud environment like Google Colab, which requires exposing the server via a public URL, please refer to our quickstart notebook:

-   [**Streamlit Quickstart Notebook**](https://github.com/Intugle/data-tools/blob/main/notebooks/quickstart_streamlit.ipynb)
