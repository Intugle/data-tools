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
pip install intugle
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

:::info

Internally, Intugle uses LangChain's `init_chat_model` function to initialize the language model. This is why the `LLM_PROVIDER` format follows [LangChain's conventions](https://python.langchain.com/docs/integrations/chat/).

:::

You can configure the LLM by setting the following environment variables:

*   `LLM_PROVIDER`: The LLM provider and model to use (for example, `openai:gpt-3.5-turbo`).
*   `API_KEY`: Your API key for the LLM provider. The exact name of the variable may vary from provider to provider.

Here's an example of how to set these variables in your environment:

```bash
export LLM_PROVIDER="openai:gpt-3.5-turbo"
export OPENAI_API_KEY="your-openai-api-key"
```

### Using a Custom LLM Instance

For environments where you need to use a pre-initialized language model, you can directly inject the model instance.

The custom LLM must be an instance of `langchain_core.language_models.chat_models.BaseChatModel`.

You can set the custom instance by modifying the `intugle.core.settings` module **before** you import and use any `intugle` classes.

**Example:**
```python
# main.py
from intugle.core import settings

# This must be an object that inherits from BaseChatModel
my_llm_instance = ... 

# Set the custom instance in the settings
settings.CUSTOM_LLM_INSTANCE = my_llm_instance

# Now, any intugle modules imported after this point will use your custom LLM

# ... rest of your code
```