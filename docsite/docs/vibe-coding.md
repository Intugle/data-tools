---
sidebar_position: 7
title: Vibe Coding
---

# Vibe Coding with the MCP Server

"Vibe Coding" is an interactive, conversational approach to data intelligence. Intugle embraces this by allowing you to serve your project as an MCP (Model Context Protocol) server.

This turns your entire data workflow into a "self-describing" resource that an AI assistant can understand and operate. It allows you to "vibe" with the intugle library—using natural language to build semantic models, perform searches, and create data products from scratch.

## 1. Setting up the MCP Server

:::info MCP Prompts
This workflow uses the capability of MCP servers to expose **prompts** to an LLM client. To use this feature, your LLM client must support the Model Context Protocol and read prompts from the MCP Server.
:::

Once you have built your semantic layer using the `SemanticModel`, you can easily expose it as a set of tools for an AI assistant by starting the built-in MCP server.

### Starting the Server

To start the server, run the following command in your terminal from your project's root directory:

```bash
intugle-mcp
```

This will start a server on `localhost:8080` by default. You should see output indicating that the server is running and that the `semantic_layer` service is mounted.

### Connecting from an MCP Client

With the server running, you can connect to it from any MCP-compatible client. The endpoint for the semantic layer is:

`http://localhost:8080/semantic_layer/mcp`

Popular clients that support MCP include AI-powered IDEs and standalone applications. Here’s how to configure a few of them:

<details>
<summary><b>Install in Cursor</b></summary>

Go to: `Settings` -> `Cursor Settings` -> `MCP` -> `Add new global MCP server`

Pasting the following configuration into your Cursor `~/.cursor/mcp.json` file is the recommended approach. See [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol) for more info.

```json
{
  "mcpServers": {
    "intugle": {
      "url": "http://localhost:8080/semantic_layer/mcp",
      "trust": true
    }
  }
}
```

</details>

<details>
<summary><b>Install in VS Code</b></summary>

Add this to your VS Code `settings.json` file. See [VS Code MCP docs](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) for more info.

```json
"mcp": {
  "servers": {
    "intugle": {
      "type": "http",
      "url": "http://localhost:8080/semantic_layer/mcp"
    }
  }
}
```

</details>

<details>
<summary><b>Install in Gemini CLI</b></summary>

See [Gemini CLI Configuration](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html) for details.

1.  Open the Gemini CLI settings file at `~/.gemini/settings.json`.
2.  Add the following to the `mcpServers` object in your `settings.json` file:

```json
{
  "mcpServers": {
    "intugle": {
      "httpUrl": "http://localhost:8080/semantic_layer/mcp",
      "trust" : true
    }
  }
}
```

If the `mcpServers` object does not exist, create it.

</details>

<details>
<summary><b>Install in JetBrains AI Assistant</b></summary>

See [JetBrains AI Assistant Documentation](https://www.jetbrains.com/help/ai-assistant/configure-an-mcp-server.html) for more details.

1. In your JetBrains IDE, go to `Settings` -> `Tools` -> `AI Assistant` -> `Model Context Protocol (MCP)`.
2. Click `+ Add`.
3. Select `As JSON` from the list.
4. Add this configuration and click `OK`:

```json
{
  "mcpServers": {
    "intugle": {
      "type": "streamable-http",
      "url": "http://localhost:8080/semantic_layer/mcp"
    }
  }
}
```

5. Click `Apply` to save changes.

</details>

<details>
<summary><b>Install in Claude Code</b></summary>

Run this command in your terminal. See [Claude Code MCP docs](https://docs.anthropic.com/en/docs/claude-code/mcp) for more info.

```sh
claude mcp add --transport http intugle http://localhost:8080/semantic_layer/mcp
```

</details>

## 2. Vibe Coding

The MCP server exposes the `intugle-vibe` prompt. This prompt equips an AI assistant with knowledge of the Intugle library and access to its core tools. You can use it to guide you through the entire data intelligence workflow using natural language.

In your MCP-compatible client, you can invoke the prompt and provide your request. In most clients, this is done by typing `/` followed by the prompt name.

### Example 1: Getting Started and Building a Semantic Model

If you are unsure how to start, you can ask for guidance. You can also ask the assistant to perform actions like creating a semantic model.

```
/intugle-vibe How do I create a semantic model?
```
```
/intugle-vibe Create a semantic model over my healthcare data.
```

The assistant will read the relevant documentation and guide you through the process or execute the steps if possible.

### Example 2: Generating a Data Product Specification

Once you have a semantic model, you can ask the assistant to create a specification for a reusable data product.

```
/intugle-vibe create a data product specification for the top 5 patients with the most claims
```

The AI assistant, connected to your MCP server, will understand that you are requesting a `product_spec`. It will use the `get_tables` and `get_schema` tools to find the `patients` and `claims` tables, and generate the specification.

### Example 3: Performing a Semantic Search

You can also perform a semantic search on your data.

```
/intugle-vibe use semantic search to find columns related to 'hospital visit reasons'
```

The assistant will code out the semantic search capabilities of your `SemanticModel` to find and return relevant columns from your datasets.

:::tip Agent Mode
Most modern, AI-powered clients support an "agent mode" where the coding assistant can handle the entire workflow for you.

For example, you can directly ask for a final output, like a CSV file:

`/intugle-vibe create a CSV of the top 10 patients by claim count`

The agent will understand the end goal and perform all the necessary intermediate steps for you. It will realize it needs to build the semantic model, generate the data product specification, execute it, and finally provide you with the resulting CSV file—all without you needing to manage the code or the process.
:::

This workflow accelerates your journey from raw data to insightful data products. Simply describe what you want in plain English and let the assistant handle the details, freeing you from the hassle of digging through documentation.
