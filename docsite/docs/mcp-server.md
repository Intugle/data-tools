---
sidebar_position: 6
title: MCP Server
---

# Intugle MCP Server

The Intugle library includes a built-in MCP (Model Context Protocol) server that exposes your data environment as a set of tools that can be understood and used by AI assistants and LLM-powered clients.

By serving your project's context through this standardized protocol, you enable powerful conversational workflows, such as [Vibe Coding](./vibe-coding.md), and allow AI agents to interact with your data securely.

## 1. Setting up the MCP Server

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

-   **Cursor**: [Configuring MCP Servers](https://docs.cursor.com/en/context/mcp#configuring-mcp-servers)
-   **Claude Code**: [Using MCP with Claude Code](https://docs.claude.com/en/docs/claude-code/mcp)
-   **Claude Desktop**: [User Quickstart](https://modelcontextprotocol.info/docs/quickstart/user/)
-   **Gemini CLI**: [Configure MCP Servers](https://cloud.google.com/gemini/docs/codeassist/use-agentic-chat-pair-programmer#configure-mcp-servers)

## 2. Data Discovery Tools

The MCP server provides tools that allow an LLM client to discover and understand the structure of your data. These tools are essential for providing the AI with the context it needs to answer questions and generate valid queries or specifications.

These tools are only available after a `SemanticModel` has been successfully generated and loaded.

### `get_tables`

This tool returns a list of all available tables in your semantic model, along with their descriptions. It's the primary way for an AI assistant to discover what data is available.

-   **Description**: Get list of tables in database along with their technical description.
-   **Returns**: A list of objects, where each object contains the `table_name` and `table_description`.

### `get_schema`

This tool retrieves the schema for one or more specified tables, including column names, data types, and other metadata including links. This allows the AI to understand the specific attributes of each table before attempting to query it.

-   **Description**: Given database table names, get the schemas of the tables.
-   **Parameters**: `table_names` (a list of strings).
-   **Returns**: A dictionary where keys are table names and values are their detailed schemas.
