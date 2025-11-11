import csv
import logging
import os

from typing import Annotated, Any, Dict, List, Optional

import pandas as pd

from langchain_core.documents import Document
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from intugle.core.conceptual_search.agent.retrievers import (
    ConceptualSearchRetrievers,
)
from intugle.core.conceptual_search.utils import (
    extract_data_product_info,
    extract_table_details,
    fetch_table_with_description,
)
from intugle.libs.smart_query_generator.models.models import (
    CategoryType,
    MeasureFunctionType,
)
from intugle.parser.manifest import Manifest

log = logging.getLogger(__name__)


class MappedAttribute(BaseModel):
    attribute_name: str
    attribute_description: str
    attribute_classification: CategoryType
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    logic: Optional[str] = None
    measure_func: Optional[MeasureFunctionType] = None


class DataProductPlannerAgentTools:
    def __init__(self, retrieval_tool: ConceptualSearchRetrievers):
        self.retrieval_tool = retrieval_tool
        self.generated_plan: Optional[pd.DataFrame] = None

    def list_tools(
        self,
    ) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                name="retrieve_existing_data_products",
                coroutine=self.retrieve_existing_data_products,
                description="""Retrieve dimensions and measures for similar existing data products.

        This function uses a retriever (retriever_dp) to fetch documents describing
        similar data products based on the input statement. It then extracts the
        data product name, its dimensions, and its measures. Includes error handling.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries. Each dictionary represents a found
                                data product and contains the keys 'Data_Product' (str),
                                'Dimensions' (List[str]), and 'Measures' (List[str]).
                                Returns an empty list ([]) if no similar products are found
                                or if a critical error occurs during the process.
        """,
            ),
            StructuredTool.from_function(
                name="retrieve_table_details",
                coroutine=self.retrieve_table_details,
                description="""
                Retrieve table details from a database based on a natural language statement.

                This function uses a retriever to fetch relevant table information based on the
                provided statement, then extracts structured details. It includes error handling
                for the retrieval and extraction steps.

                Returns:
                List[Dict[str, Any]]: A list of dictionaries, where each dictionary contains
                                extracted details of a potentially relevant table (e.g.,
                                {'Table_Name': ..., 'Description_Snippet': ...}).
                                Returns an empty list ([]) if no relevant tables are
                                found or if a critical error occurs during retrieval/extraction.
                                """,
            ),
            StructuredTool.from_function(
                self.save_data_product,
                name="save_data_product",
                description="""
                Processes a list of attribute dictionaries and saves them
                with detailed print statements for monitoring.

                Each dictionary in the input list should represent a single attribute,
                with the attribute name as the key and a list containing
                [description, classification ('Dimension'/'Measure')] as the value.

                Returns:
                A string message indicating success or failure.
                """,
            ),
        ]

    async def retrieve_existing_data_products(
        self,
        statement: Annotated[
            str,
            """Name or description of the data product you want to search for
                            (e.g., 'sales dashboard', 'customer churn analysis').""",
        ],
    ) -> List[Dict[str, Any]]:
        log.info(f"--- Executing retrieve_existing_data_products for statement: '{statement}' ---")
        try:
            documents = await self.retrieval_tool.data_products_retriever(statement)
            log.info(f"Retriever returned {len(documents)} potential document(s).")

            if not documents:
                log.info("No similar data product documents were found by the retriever.")
                return []

            result = extract_data_product_info(documents)
            log.info(f"Extraction process resulted in {len(result)} structured data product detail(s).")
            return result
        except Exception as e:
            log.error(f"ERROR: An exception occurred during data product retrieval: {e}", exc_info=True)
            raise e

    async def retrieve_table_details(
        self,
        statement: Annotated[
            str,
            """A natural language description of the table name and/or
                            purpose you are searching for (e.g., "customer information table",
                            "table containing order line items").""",
        ],
    ) -> List[Dict[str, Any]]:
        log.info(f"--- Executing retrieve_table_details for statement: '{statement}' ---")
        try:
            documents = await self.retrieval_tool.table_retriever(statement)
            log.info(f"Retriever returned {len(documents)} potential document(s).")

            if not documents:
                log.info("No relevant table documents were found by the retriever for the given statement.")
                return ["No relevant table documents were found by the retriever for the given statement."]

            result = extract_table_details(documents)
            log.info(f"Extraction process resulted in {len(result)} structured table detail(s).")
            return result
        except Exception as e:
            log.error(f"ERROR: An exception occurred during detail extraction: {e}", exc_info=True)
            return [f"ERROR: An exception occurred during detail extraction: {e}"]

    def save_data_product(
        self,
        data_product_name: Annotated[str, "Name of the data product"],
        data_product_description: Annotated[
            str, "Short description of the data product"
        ],
        attribute_data: Annotated[
            List[Dict[str, List[str]]],
            """A list of dictionaries. in the form of:
            Syntax: [{'Attribute Name':['Attribute description','Classification of attribute i.e. `Dimension' or `Measure`]}]

            Example: [{'Customer ID': ['Unique identifier', 'Dimension']},{'Sales Amount': ['Total sales value', 'Measure']}]
            """,
        ],
    ) -> str:
        log.info(f"--- Starting save_data_product Tool for '{data_product_name}'---")
        filename = "attributes.csv"

        if not isinstance(attribute_data, list):
            error_msg = "Error: Input data must be a list."
            log.error(error_msg)
            return error_msg

        processed_data = []
        headers = [
            "Data Product Name",
            "Data Product Description",
            "Attribute Name",
            "Attribute Description",
            "Attribute Classification",
        ]

        for item in attribute_data:
            if not isinstance(item, dict) or len(item) != 1:
                error_msg = f"Error: Item must be a dictionary with a single attribute. Found: {item}"
                log.error(error_msg)
                return error_msg

            try:
                attribute_name, details = list(item.items())[0]
                if not isinstance(details, list) or len(details) != 2:
                    error_msg = f"Error: Value for '{attribute_name}' must be a list of [description, classification]."
                    log.error(error_msg)
                    return error_msg

                description, classification = details
                processed_data.append(
                    {
                        "Data Product Name": data_product_name,
                        "Data Product Description": data_product_description,
                        "Attribute Name": attribute_name,
                        "Attribute Description": description,
                        "Attribute Classification": classification,
                    }
                )
            except Exception as e:
                error_msg = f"An unexpected error occurred while processing item {item}: {e}"
                log.error(error_msg, exc_info=True)
                return error_msg

        self.generated_plan = pd.DataFrame(processed_data, columns=headers)

        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(processed_data)
            full_path = os.path.abspath(filename)
            success_msg = f"Successfully created and saved attribute data to {full_path}. You can now EXIT"
            log.info(success_msg)
            return success_msg
        except IOError as e:
            error_msg = f"Error: Could not write to file {filename}. Check permissions or path. Reason: {e}"
            log.error(error_msg, exc_info=True)
            return error_msg


class DataProductBuilderAgentTools:
    def __init__(
        self,
        retrieval_tool: ConceptualSearchRetrievers,
        manifest: Manifest,
    ):
        self._retrieval_tool = retrieval_tool
        self.manifest = manifest
        self.column_logic_results: List[MappedAttribute] = []
        self.table_description = None

    def list_tables(
        self,
    ) -> List[Dict[str, str]]:
        """
        Retrieve a list of unique tables from the dataset along with their glossary and domain information.
        Returns:
        List[Dict[str, str]]: A list of dictionaries, each containing:
            - 'table_name': The name of the table.
            - 'table_glossary': A description of what the table contains.
            - 'table_domain': The domain or subject area the table belongs to.
        """
        if self.table_description is None:
            self.table_description = fetch_table_with_description(
                self.manifest
            ).drop_duplicates()
        return self.table_description.to_dict(orient="records")

    def column_logic_store(
        self,
        attribute_name: Annotated[str, "Name of the attribute that was mapped."],
        attribute_description: Annotated[str, "Description of the attribute."],
        attribute_classification: Annotated[
            CategoryType,
            "Classification of the attribute as 'dimension' or 'measure'.",
        ],
        column_table_combined: Annotated[
            Optional[str],
            "A single string in the format 'column_name$$##$$table_name'. Use this if a direct column mapping is found. Set to None if no mapping is found.",
        ],
        logic: Annotated[
            Optional[str],
            "The transformation or aggregation logic (e.g., 'SUM', 'COUNT', or a SQL expression).",
        ],
        measure_func: Annotated[
            Optional[MeasureFunctionType],
            "The aggregation function for a measure (e.g., 'sum', 'count'). Required if attribute_classification is 'measure'.",
        ],
    ) -> str:
        """
        Stores the derived logic for a single data product attribute.
        """
        table_name, column_name = None, None
        if column_table_combined:
            try:
                column_name, table_name = column_table_combined.split("$$##$$")
            except ValueError:
                return f"[Error] Invalid format in '{column_table_combined}' (expected 'column_name$$##$$table_name')"

        if (
            attribute_classification == CategoryType.measure
            and measure_func is None
        ):
            return "[Error] For a 'measure' attribute, 'measure_func' is required."

        mapped_attribute = MappedAttribute(
            attribute_name=attribute_name,
            attribute_description=attribute_description,
            attribute_classification=attribute_classification,
            table_name=table_name,
            column_name=column_name,
            logic=logic,
            measure_func=measure_func,
        )
        self.column_logic_results.append(mapped_attribute)

        return f"[Stored] Successfully stored logic for attribute: {attribute_name}"

    async def column_retriever(
        self,
        table_names: Annotated[
            List[str], "A list of table names to restrict the search to."
        ],
        attribute_name: Annotated[
            str, "The name of the attribute to search for (e.g., 'Count of Products')."
        ],
        attribute_description: Annotated[
            str,
            "A description of what the attribute represents.",
        ],
    ) -> List[Dict[str, str]]:
        """
        Retrieves relevant columns from the provided list of tables that semantically match the given attribute name and description.

        Args:
            table_names (List[str]): A list of table names to restrict the search to.
            attribute_name (str): The name of the attribute to search for (e.g., "Count of Products").
            attribute_description (str): A description of what the attribute represents.

        Returns:
            List[Dict[str, str]]: A deduplicated list of dictionaries, each containing:
                - 'table_name': The table the column belongs to
                - 'column_name': The name of the relevant column
        """
        retrieved_results = await self._retrieval_tool.column_retriever(
            attribute_name=attribute_name, attribute_description=attribute_description
        )

        if not retrieved_results:
            return "No appropriate column was found."

        def filter_by_table(doc: Document) -> bool:
            return doc.metadata.get("table") in table_names

        if table_names:
            retrieved_results = list(filter(filter_by_table, retrieved_results))

        return [
            {
                "table_name": result.metadata["table"],
                "column_name": result.metadata["column"],
                "column_glossary": result.page_content,
            }
            for result in retrieved_results
        ]

    def list_tools(
        self,
    ) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                func=self.list_tables,
                name="list_tables",
                description="""
                  Retrieve a list of unique tables from the dataset along with their glossary and domain information.
                  Returns:
                  List[Dict[str, str]]: A list of dictionaries, each containing:
                  - 'table_name': The name of the table.
                  - 'table_glossary': A description of what the table contains.
                  - 'table_domain': The domain or subject area the table belongs to.
                """,
            ),
            StructuredTool.from_function(
                func=self.column_logic_store,
                name="column_logic_store",
                description="""Stores the derived logic for a single data product attribute.""",
            ),
            StructuredTool.from_function(
                coroutine=self.column_retriever,
                name="column_retriever",
                description="""Retrieves relevant columns from the provided list of tables that semantically match the given attribute name and description.
                Returns:
                List[Dict[str, str]]: A deduplicated list of dictionaries, each containing:
                - 'table_name': The table the column belongs to
                - 'column_name': The name of the relevant column
                - 'column_glossary': The business description of the column
                """,
            ),
        ]
