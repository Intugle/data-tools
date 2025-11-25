import json

from typing import Annotated, List, Optional, Sequence, TypedDict

import pandas as pd

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from intugle.adapters.adapter import Adapter
from intugle.adapters.models import DataSetData
from intugle.core.llms.chat import ChatModelLLM
from intugle.core.observability import get_langfuse_handler
from intugle.core.settings import settings


# Structured Response from Agent
class PrimaryKeyResponse(BaseModel):
    key: Optional[List[str]] = Field(
        description="Return list of fields/s for composite key or single primary key, None if no primary key found"
    )


# Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    remaining_steps: int = 25
    table_name: str
    structured_response: PrimaryKeyResponse


# DDL Generation Dtype Mapping
DTYPE_MAPPING = {
    "integer": "INTEGER",
    "float": "FLOAT",
    "date & time": "DATETIME",
    "close_ended_text": "TEXT",
    "open_ended_text": "TEXT",
    "alphanumeric": "TEXT",
    "others": "TEXT",
    "range_type": "TEXT",
}


class KeyIdentificationAgent:
    COMPOSITE_KEY_THRESHOLD = 0.98
    SINGLE_KEY_THRESHOLD = 1.0
    COMPLETENESS_THRESHOLD = 1.0

    def __init__(self, profiling_data: pd.DataFrame, adapter: Adapter, dataset_data: DataSetData):
        self.profiling_data = profiling_data
        self.dataset_data = dataset_data
        self.adapter = adapter
        self.table_name = self.profiling_data["table_name"].iloc[0]
        self.composite_key_cache: dict = {}
        self.llm = ChatModelLLM.build(
            model_name=settings.LLM_PROVIDER,
            llm_config={"temperature": 0.2, "timeout": 60},
        )

        # Define tools as methods bound to the instance
        bound_uniqueness_check_composite_key = self._uniqueness_check_composite_key
        bound_validate_key = self._validate_key

        # Decorate the bound methods with the @tool decorator
        self.uniqueness_check_composite_key_tool = tool(
            bound_uniqueness_check_composite_key
        )
        self.validate_key_tool = tool(bound_validate_key)

    def _generate_ddl_statement(self) -> str:
        """Generates a rich DDL statement with profiling info in comments."""
        table_columns = self.profiling_data["column_name"].to_list()
        column_datatypes = \
            self.profiling_data[["column_name", "datatype_l1"]] \
            .set_index("column_name") \
            .to_dict()["datatype_l1"]

        create_table_query = f"CREATE TABLE {self.table_name} ("
        column_parts = []

        for column in table_columns:
            parts = []
            parts.append(f'"{column}"')

            datatype = DTYPE_MAPPING.get(column_datatypes.get(column), "TEXT")
            parts.append(datatype)

            # Embed profiling info as a comment
            try:
                profiling_info = self.profiling_data.loc[
                    self.profiling_data["column_name"] == column,
                    [
                        "datatype_l1",
                        "distinct_count",
                        "uniqueness",
                        "completeness",
                        "sample_data",
                    ],
                ].to_dict(orient="records")[0]

                # Format for readability
                profiling_info["uniqueness"] = f'{profiling_info["uniqueness"]:.2%}'
                profiling_info["completeness"] = f'{profiling_info["completeness"]:.2%}'
                profiling_info["sample_data"] = str(profiling_info["sample_data"])

                profiling_str = \
                    json.dumps(profiling_info) \
                    .replace("{", "") \
                    .replace("}", "") \
                    .replace('"', "")
                parts.append(f"-- {profiling_str}")
            except (IndexError, KeyError):
                pass  # No profiling info for this column

            column_parts.append(" ".join(parts))

        create_table_query = \
            create_table_query + "\n    " + ",\n    ".join(column_parts) + "\n);"
        return create_table_query

    def _validate_key(self, fields: List[str]) -> str:
        """
        Returns information regarding the validity of primary / composite key
        Args:
            fields (List[str]): primary key or composite key

        Returns:
            str: Returns feedback of key verification
        """
        feedbacks = []

        # Uniqueness check
        if len(fields) == 1:
            field = fields[0]
            uniqueness = self.profiling_data.loc[
                self.profiling_data["column_name"] == field, "uniqueness"
            ].values[0]
            if uniqueness < self.SINGLE_KEY_THRESHOLD:
                feedbacks.append(
                    f"{field} has only {uniqueness:.2%} uniqueness, which is below the threshold of {self.SINGLE_KEY_THRESHOLD:.0%}"
                )

        # Completeness check for all fields
        for field in fields:
            completeness = self.profiling_data.loc[
                self.profiling_data["column_name"] == field, "completeness"
            ].values[0]
            if completeness < self.COMPLETENESS_THRESHOLD:
                feedbacks.append(
                    f"{field} is only {completeness:.2%} complete, which is below the completeness threshold of {self.COMPLETENESS_THRESHOLD:.0%}"
                )

        if not feedbacks:
            return "Everything is good and validated."

        return "\n- ".join(feedbacks)

    def _uniqueness_check_composite_key(self, fields: List[str]) -> str:
        """
        Retrieves the information for the uniqueness by combining multiple fields.

        Args:
            fields (List[str]): List of fields that are potential candidate for primary key

        Returns:
            str: A summary description on the uniqueness of the combined fields.
        """
        if not fields or len(fields) < 2:
            return "This tool is for checking composite keys. Please provide at least two fields."

        try:
            distinct_count = self.adapter.get_composite_key_uniqueness(
                table_name=self.table_name, columns=fields, dataset_data=self.dataset_data
            )
            cache_key = tuple(sorted(fields))
            self.composite_key_cache[cache_key] = distinct_count

            total_count = self.profiling_data["count"].iloc[0]

            if total_count > 0:
                uniqueness = round(distinct_count / total_count, 4)
            else:
                uniqueness = 0

            msg = f"which meets the threshold score of {self.COMPOSITE_KEY_THRESHOLD:.0%} for a composite key."
            if uniqueness < self.COMPOSITE_KEY_THRESHOLD:
                msg = f"which does not meet the threshold score of {self.COMPOSITE_KEY_THRESHOLD:.0%} for a composite key."

            return f"The combined uniqueness of fields {', '.join(fields)} is {uniqueness:.2%}, {msg}"

        except Exception as e:
            return f"Error executing uniqueness check for composite key {fields}: {e}"

    def __call__(self):
        key_identification_agent_prompt = ChatPromptTemplate(
            messages=[
                (
                    "system",
                    """
Task: Identify the Primary Key (Single or Composite) for a database table using its schema and profiling metadata.
- Use the provided DDL, which includes profiling statistics as comments, to determine the most likely primary key.
- Follow the steps below for both single and composite key identification.

# General Rules
1. **No Nulls Allowed**: A primary key must not have null values. Check the `completeness` metric. It must be 100%.
2. **High Uniqueness**: A primary key must uniquely identify each row. Check the `uniqueness` metric. It must be 100% for a single key.
3. **Exclude Timestamps**: Do not consider fields like `created_date`, `modified_date`, or `updated_date` as primary keys.

# Single Primary Key Identification
1. **Check Uniqueness & Completeness**: Identify fields with 100% uniqueness and 100% completeness.
2. **Assess Semantic Meaning**: Consider field names and the table name. For example, `patient_id` is a likely primary key for a `patients` table.
3. If a valid single-field key is found, **STOP HERE** and validate it.

# Composite Primary Key Identification
1. Only consider composite keys **if no single primary key** is found.
2. Select the **most plausible combination** of fields based on semantics. The combination should logically form a unique identifier.
3. Once a candidate composite key is chosen, you MUST validate it using the `uniqueness_check_composite_key` tool.
4. If multiple combinations could work, select the one with the fewest columns that is most semantically meaningful.

# Final Validation
- Before returning your final answer, you MUST use the `validate_key` tool on your chosen single or composite key to confirm it meets all criteria.
""",
                ),
                ("human", "{messages}"),
            ]
        )

        agent_tools = [self.uniqueness_check_composite_key_tool, self.validate_key_tool]

        agent = create_react_agent(
            model=self.llm.model,
            tools=agent_tools,
            prompt=key_identification_agent_prompt,
            state_schema=AgentState,
            response_format=PrimaryKeyResponse,
        )

        table_schema = self._generate_ddl_statement()

        # Get Langfuse handler if enabled
        langfuse_handler = get_langfuse_handler(trace_name=f"key-id-{self.table_name}")
        config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}

        result = agent.invoke(
            input={
                "messages": [("user", f"#Input Schema:\n{table_schema}")],
                "table_name": self.table_name,
            },
            config=config,
        )

        response = result.get("structured_response")
        if not (response and response.key):
            return {}

        key_columns = response.key
        distinct_count = None

        if len(key_columns) > 1:
            cache_key = tuple(sorted(key_columns))
            distinct_count = self.composite_key_cache.get(cache_key)
        elif len(key_columns) == 1:
            # It's a single key, get the distinct count from profiling data
            try:
                distinct_count = self.profiling_data.loc[
                    self.profiling_data["column_name"] == key_columns[0],
                    "distinct_count",
                ].iloc[0]
            except (IndexError, KeyError):
                distinct_count = None  # Should not happen if data is consistent

        return {"columns": key_columns, "distinct_count": distinct_count}
