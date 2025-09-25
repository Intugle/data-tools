---
sidebar_position: 5
title: Vibe Coding
---

# Vibe Coding with the MCP Server

"Vibe Coding" is an interactive, conversational approach to development where you use natural language to generate code or specifications. Intugle embraces this by allowing you to serve your semantic layer through an MCP (Model Context Protocol) server.

This turns your data into a "self-describing" resource that an AI assistant can understand, allowing you to "vibe" with your data to create specifications without writing them by hand.

:::info In Progress
Currently, Vibe Coding is available for generating **Data Product** specifications. We are actively working on extending this capability to other modules in the Intugle ecosystem. Stay tuned for more updates!
:::

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

This will start a server on `localhost:8000` by default. You should see output indicating that the server is running and that the `semantic_layer` and `adapter` services are mounted.

### Connecting from an MCP Client

With the server running, you can connect to it from any MCP-compatible client. The endpoint for the semantic layer is:

`http://localhost:8000/semantic_layer/mcp`

Popular clients that support MCP include AI-powered IDEs and standalone applications. Here’s how to configure a few of them:

-   **Cursor**: [Configuring MCP Servers](https://docs.cursor.com/en/context/mcp#configuring-mcp-servers)
-   **Claude Code**: [Using MCP with Claude Code](https://docs.claude.com/en/docs/claude-code/mcp)
-   **Claude Desktop**: [User Quickstart](https://modelcontextprotocol.info/docs/quickstart/user/)
-   **Gemini CLI**: [Configure MCP Servers](https://cloud.google.com/gemini/docs/codeassist/use-agentic-chat-pair-programmer#configure-mcp-servers)

## 2. Using Vibe Coding

The MCP server exposes powerful prompts that are designed to take your natural language requests and convert them directly into valid specifications.

### Example: Generating a Data Product

Currently, you can use the `create-dp` prompt to generate a `product_spec` dictionary for a Data Product.

In your MCP-compatible client, you can invoke the prompt and provide your request. In most clients, this is done by typing `/` followed by the prompt name.

```
/create-dp show me the top 5 patients with the most claims
```

:::tip Client-Specific Commands
The exact command to invoke a prompt (e.g., using `/` or another prefix) can vary between clients. Be sure to check the documentation for your specific tool.
:::

The AI assistant, connected to your MCP server, will understand the request, use the `get_tables` and `get_schema` tools to find the `patients` and `claims` tables, and generate the following `product_spec`:

```json
{
  "name": "top_5_patients_by_claims",
  "fields": [
    {
      "id": "patients.first",
      "name": "first_name"
    },
    {
      "id": "patients.last",
      "name": "last_name"
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
    "limit": 5
  }
}
```

This workflow allows you to stay in your creative flow, rapidly iterating on data product ideas by describing what you want in plain English.
