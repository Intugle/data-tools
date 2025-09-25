---
sidebar_position: 2
---

# Getting started

## Installation

For Windows and Linux, you can follow these steps. For macOS, please see the extra steps in the macOS section below.

Before installing, we recommend creating a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Then, install the package:

```bash
pip install intugle==0.1.10
```

### macOS

For macOS users, you may need to install the `libomp` library:

```bash
brew install libomp
```

If you installed Python using the official installer from python.org, you may also need to install SSL certificates by running the following command in your terminal. Please replace `3.XX` with your specific Python version. This step isn't necessary if you installed Python using Homebrew.

```bash
/Applications/Python\ 3.XX/Install\ Certificates.command
```

## Configuration

Before running the project, you need to configure a Large Language Model (LLM). The library uses the LLM for tasks like generating business glossaries and predicting links between tables.

You can configure the LLM by setting the following environment variables:

*   `LLM_PROVIDER`: The LLM provider and model to use (for example, `openai:gpt-3.5-turbo`) following LangChain's [conventions](https://python.langchain.com/docs/integrations/chat/)
*   `API_KEY`: Your API key for the LLM provider. The exact name of the variable may vary from provider to provider.

Here's an example of how to set these variables in your environment:

```bash
export LLM_PROVIDER="openai:gpt-3.5-turbo"
export OPENAI_API_KEY="your-openai-api-key"
```