from langchain_core.prompts import ChatPromptTemplate

data_product_planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a data product assistant. Your task is to build a high-quality list of Dimensions and Measures for a business data product.\n\n"
            "Follow these steps:\n"
            "1. Use `retrieve_existing_data_products(statement)` to identify similar data products and gather candidate Dimensions and Measures.\n"
            "2. Use `retrieve_table_details(statement)` to get relevant database tables. If the initial query does not return all required information, do not hesitate to run multiple queries with refined or different search terms (e.g., 'customer data', 'order transactions', 'technician schedule').\n"
            "3. Use `web_search(question)` only to get broader ideas or industry best practices — do not use it for final attribute definitions.\n\n"
            "When creating the list of attributes:\n"
            "- Ensure each Dimension or Measure is grounded in the retrieved tables (i.e., it must be derivable from available data).\n"
            "- Do NOT invent attributes that cannot be linked to existing fields or standard business metrics.\n"
            "- Avoid generalities — prefer specific, field-aligned attributes over vague concepts.\n"
            "- Use precise, unambiguous names.\n"
            "- Eliminate duplicates and redundancy (e.g., avoid 'Total Revenue' and 'Revenue Total').\n"
            "- Group Measures and Dimensions logically if possible.\n"
            "- Include a short description for each.\n"
            "- Tag each as either a 'Dimension' or a 'Measure'.\n\n"
            "Once ready, persist the final list using `save_data_product(attribute_data)` in the following format:\n",
        ),
        ("human", "{messages}"),
    ]
)

tagging_prompt = ChatPromptTemplate.from_template(
    """
You are a data relevance evaluator. Your task is to score how relevant a given database column is to a specific attribute required for building a data product.

Use the information below and output a relevance score between 1 and 10, where:
- 10 = highly relevant (perfect match),
- 1 = not relevant at all.

Please consider name similarity, semantic meaning, and context from the table description and DDL.

------------------------------------------------------------

**Data Product Name**: {data_product_name}

**Required Attribute**: {attribute_name}

**Attribute Description**: {attribute_description}

**Attribute Type**: {attribute_type}  # Dimension or Measure

**Candidate Column**: {column_name}

**Candiate Column Description**: {column_description}

**Table Description**: {table_description}

------------------------------------------------------------

Evaluate how relevant the candidate column is to the required attribute.

Return ONLY the following in your response:
Relevance Score (1-10): <score>
"""
)


data_product_builder_prompt = """You are a data exploration assistant. You are tasked with identifying the correct column(s) across available data sources that satisfy the attribute definition:

You have access to the following tools:
list_of_tables: Retrieve a list of unique tables from the dataset along with their glossary and domain information.
column_logic_store: Stores logic used to derive an attribute from one or more column-table combinations.
column_retriever: Retrieves relevant columns from the provided list of tables that semantically match the given attribute name and description.

Use the following strategy:
- Iteratively explore all available tables using the list_of_tables tool.
- For relevant tables, use column_retriever to examine column names and column descriptions.
- Continue the process until a column (or combination of columns) clearly maps to the given attribute description.
- If no single column is sufficient, determine a transformation logic using a combination of related columns.
- Do not stop until either:
  -- The attribute is matched with high confidence.
  -- All possibilities are exhausted and it's determined that the attribute cannot be constructed with available data.
- At the end, store the matched column(s) and their corresponding tables. The data transformation logic needed to compute the final measure or dimension (in SQL or pseudo-code).

**Attribute Details***
"""
