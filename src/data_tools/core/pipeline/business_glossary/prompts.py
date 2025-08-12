from langchain.output_parsers import ResponseSchema

table_glossary = [ResponseSchema(name="table_glossary", description=" single-sentence business glossary definition")]
column_glossary = [ResponseSchema(name="column_glossary", description="precise, single-sentence and non-technical business glossary definition")]
column_tag_glossary = [ResponseSchema(name="column_tag_glossary", description="three precise and distinct business tags", type="list[str]")]

BUSINESS_GLOSSARY_PROMPTS = {
"gpt-4o": {
"TABLE_GLOSSARY_TEMPLATE": """You are responsible for Data Governance in {domain},
generate a concise, non-technical business glossary definition for the table on a provided DDL statement.
The definition should be written as a single sentence and clearly describe the business purpose or function.\n
# Instructions
- **Interpret the table name**: Provide a one-sentence, non-technical summary of the table's role from a business perspective (e.g., what type of business entity or process it represents).
- **Input format**: The input will be a DDL statement defining the schema of a table, including table name, columns, and data types. Comments prefixed by `--` may provide contextual hints.
- **Output format**: DONOT mention table name in the glossary description. DONOT start sentence with 'this table'.\n
- **Additional Context**: if provided, `Additional Context` may provide more information about the data.

# Input
{create_statements}
\n
# Additional Context:
{additional_context}\n
# Output
{format_instructions}    
""",
"BUSINESS_GLOSSARY_TEMPLATE": """You are responsible for Data Governance in {domain},
generate a concise single-sentence business glossary definition for each column mentioned in the DDL statement.\n
The definition should clearly describe the business purpose or function.\n

# Instructions:
1.Parse the DDL statement defining the schema, which includes the table name, column names, data types, and any comments (prefixed by --), which may provide additional context about the column.
2.Provide a single-sentence, non-technical business glossary definition for each column, describing what the column represents and how it is used within the business context.
3.If the comment or the name of the column suggests a specific business process, use that context to shape the definition.
4.Don't mention data values in description or any statistics in description.\n\n
5.If provided `Additional Context` may provide more information about the data.

# Input
{create_statements}\n
{format_instructions}
""",
"BUSINESS_TAGS_TEMPLATE": """You are responsible for Data Governance in {domain}, your task is to generate three business tags for a column based on the DDL statements of a table given below.
Use the column's context within the DDL statement (e.g., its name, type, and table name) to infer relevant business tags. Focus on generating concise, domain-relevant, 
and meaningful tags that align with the potential business use of the column.

# Instructions
1. **Parsing the DDL Statement:**  
- Consider the table name and other column definitions ( like sample data) to infer contextual meaning.
- Don't mention data values in description or any statistics in description.

2. **Tag Principles:**  
- Tags should be descriptive of the column's business context, not just technical.
- Tags can represent the purpose, or connection to broader business use.

3. **Number of Tags:**  
- Always generate exactly three distinct business tags.

4. **Language and Style:**  
- Prefer title case consistently across all tags.

5. **Additional Context**
- If provided `Additional Context` may provide more information about the data.

# Input
{create_statements}\n
# Additional Context:
{additional_context}\n
{format_instructions}
"""
},
"gpt-4o-mini": {
"TABLE_GLOSSARY_TEMPLATE": """
Role: You are responsible for Data Governance in the {domain}.\n
Task: You will be given a SQL DDL statement how `{table}` table is structured. Generate a concise, non-technical business glossary definition for `{table}` that clearly describe the business purpose or function.\n

Instructions:\n
- Parse and interpret SQL DDL statement, including attribute names. Comments prefixed but `--` may provide contextual hints.
- Provide a single-sentence, non-technical summary of the table's role from a business perspective (e.g., what type of business entity or process it represents).
- If the comment or the name of the attribute name , or name of the table suggests a specific business process, use that context to shape the definition.
- The glossary should begin with defintion followed by the business role.
- DONOT mention table name in the glossary. 
- DONOT start sentence with either `This table` or `This entity`, or with noun phrase or demonstrative pronoun or `Represents`.
- DONOT mention {domain} in the glossary.
- If provided, `Additional Context` may provide more information about the data.

#Input:\n
{create_statements}\n
# Additional Context:
{additional_context}
\n\n
{format_instructions}
""",
"BUSINESS_GLOSSARY_TEMPLATE": """
Role: You are responsible for Data Governance in the {domain}.\n
Task: You will be given a SQL DDL statement how the attribute `{column}` is structured.\n

Instruction:
1. Interpret the attribute name `{column}`, i.e what type of business entity or process it represents.
2. Parse and interpret SQL DDL statement, including attribute `{column}`. Comments prefixed but `--` may provide contextual hints.
3. Provide a precise single-sentence, non-technical glosary of the attribute `{column}` role from a business perspective.
4. If the comment or the name of the attribute or name of the table suggests a specific business process, use that context to shape the definition.
5. DONOT mention any data values.
6. DONOT include any assumptions.
7. DONOT include attribute name `{column}` in the glossary.
8. DONOT start the glossary with noun phrase or demonstrative pronoun or `This attribute` or `Represents`.
9. DONOT mention {domain} in the glossary.
10. If provided, `Additional Context` may provide more information about the data.\n

#Input:\n
{create_statements}\n
# Additional Context:
{additional_context}\n\n
{format_instructions}
""",
"BUSINESS_TAGS_TEMPLATE":
"""
Role: You are responsible for Data Governance in the {domain}.\n
Task: You will be given a SQL DDL statement how the attribute `{column}` is structured.\n

Instruction:
1. Interpret the attribute name `{column}`, i.e what type of business entity or process it represents.
2. Parse and interpret SQL DDL statement, including attribute `{column}`. Comments prefixed but `--` may provide contextual hints.
3. Focus on generating concise and meaningful tags that align with the potential business use of the column.
4. Tags should be descriptive of the  attribute business context, not just technical.
5. Tags are keywords or labels that can represent the purpose, or connection to broader business use.
6. ALWAYS generate exactly three distinct business tags.
7. Prefer title case consistently across all tags.
8. If provided, `Additional Context` may provide more information about the data.\n

#Input\n
{create_statements}\n
# Additional Context:
{additional_context}\n\n
{format_instructions}
"""
}
}