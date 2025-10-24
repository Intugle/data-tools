import textwrap

from pathlib import Path

import aiofiles

from intugle.mcp.docs_search.service import docs_search_service
from intugle.mcp.semantic_layer.schema import SQLDialect


class Prompts:
    """
    LLM Prompts used by executor server
    """

    @classmethod
    async def intugle_vibe_prompt(cls, user_query: str = "") -> str:
        """
        Returns the prompt for the Intugle Vibe agent.
        """
        prompt_path = Path(__file__).parent / "prompts" / "intugle_vibe_prompt.md"
        async with aiofiles.open(prompt_path, "r") as f:
            base_prompt = await f.read()

        library_overview = textwrap.dedent("""
            Intugle is a GenAI-powered open-source Python library that builds a semantic data model over your existing data systems.
            It discovers meaningful links and relationships across data assets, enriching them with profiles, classifications, and business glossaries.
            With this connected knowledge layer, you can enable semantic search and auto-generate queries to create unified data products,
            making data integration and exploration faster, more accurate, and far less manual.
        """)

        doc_paths = await docs_search_service.list_doc_paths()
        formatted_doc_paths = "\n".join(f"- `{path}`" for path in doc_paths)

        query_section = ""
        if user_query:
            query_section = f"Conversation starts:\n\n---\n\n{user_query}"

        return base_prompt.format(
            library_overview=library_overview.strip(),
            doc_paths=formatted_doc_paths,
            user_query=query_section
        )

    # @classmethod
    # def create_dp_prompt(cls, user_request: str) -> str:
    #     """
    #     Returns the prompt for creating a data product specification.
    #     """
    #     prompt_path = Path(__file__).parent / "prompts" / "create_dp_prompt.md"
    #     with open(prompt_path, "r") as f:
    #         base_prompt = f.read()
    #     return base_prompt.format(user_request=user_request)

    @classmethod
    def raw_executor_prompt(
        cls,
        dialect: SQLDialect,
        domain: str = "Industry",
        universal_instructions: str = "",
    ) -> str:
        """
        Given a dialect returns the appropriate executor agent prompt ( prompt for handling)
        Args:
            dialect (SQLDialect): _description_

        Returns:
            str: _description_
        """

        prompt = textwrap.dedent("""
        You are a Business Intelligence (BI) assistant with access to a {source} database from {domain}. Your role is to help users explore the data, extract useful insights, and answer their questions using available tools.

        Tools:
        - `get_tables`: Retrieve a list of all available tables.
        - `get_schema`: Get the schema details for a specified tables
        - `execute_query`: Run queries using the specified {dialect} dialect.
        - `get_user_guidance`: Access relevant examples and helpful logic for building effective queries.
        - `global_semantic_search_entity`: Perform semantic search across all data fields to find meaningful matches.
        - `targeted_semantic_search_entity`: Perform semantic search on a specific data field to find meaningful matches.

        Instructions:
        1. Building a plan:
        - First ALWAYS analyse the user question and available tools and build a proper plan.
        - ALWAYS break down the user question logically before acting.
        - You can **revise** , **modify** or **update** the plan.
        2. Then ALWAYS use `get_tables` to see what tables are available.
        3. ALWAYS use `get_user_guidance` to retrive any business-defined logic, get sample query example and logic definitions.
        4. ALWAYS use `get_schema` to explore table structure before querying.
        5. Text Formatting: For 'ALPHANUMERIC', 'CLOSE_ENDED_TEXT', and 'OPEN_ENDED_TEXT' columns, convert all query values (in WHERE clauses and selected columns) to lowercase and remove leading/trailing whitespace. **No trim** and **case standardisation** for columns of datatype "INTEGER" , "FLOAT" and columns involved in SQL JOIN's.
        6. Use `execute_query` for executing queries.
        7. Correct the query by ensuring function compatibility with the {dialect}, fixing syntax issues, handling edge cases (e.g., NULLs, division by zero, case sensitivity, whitespace), and re-testing using the `execute_query` tool.
        8. Use either `global_semantic_search_entity` or `targeted_semantic_search_entity` to resolve entity ambiguity or empty results by performing semantic search on shortlisted fields, falling back to pattern or logic-based queries for others. 
        9. Use `targeted_semantic_search_entity` if you want to do a semantic search within a specific column of a table, use `global_semantic_search_entity` if not sure about the column within which you want to do a search.
        10. Handle errors gracefully:
        - Explain failures.
        - Suggest corrections or alternatives.
        11. Proactive Clarification and Disambiguation:
        Pause and request clarification from the user only after you have analyzed all relevant tables and table schemas and checked for user guidance, and still:
            - The query remains ambiguous, incomplete, or uses undefined terms, or
            - The result of execute_query has multiple possible interpretations.    
            When asking for clarification, always ground your question in findings obtained through appropriate tools to ensure the clarification is relevant and well-informed.

        {universal_instructions}

        NOTE: **Think step-by-step and communicate clearly and concisely**
        """)

        if len(universal_instructions.strip()) != 0:
            universal_instructions = f"""\n\n## Universal Instructions (MUST FOLLOW): \n{universal_instructions}"""

        dialect_prompts = {
            SQLDialect.SQLITE: prompt.format(
                source=dialect,
                dialect=dialect.prompt_dialect,
                domain=domain,
                universal_instructions=universal_instructions,
            ),
            SQLDialect.POSTGRES: prompt.format(
                source=dialect,
                dialect=dialect.prompt_dialect,
                domain=domain,
                universal_instructions=universal_instructions,
            ),
            SQLDialect.MSSQL: prompt.format(
                source=dialect,
                dialect=dialect.prompt_dialect,
                domain=domain,
                universal_instructions=universal_instructions,
            ),
        }
        return dialect_prompts[dialect]
