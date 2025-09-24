import logging
import time

from enum import Enum
from typing import List, Optional, Tuple

import pandas as pd

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.errors import GraphRecursionError
from tqdm import tqdm

from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.core.llms.chat import ChatModelLLM
from intugle.core.pipeline.link_prediction.utils import (
    dtype_check,
    extract_innermost_dict,
    linkage,
    preprocess_profiling_df,
)
from intugle.core.utilities.llm_utils import (
    generate_create_table_query,
    read_column_datatypes,
)

log = logging.getLogger(__name__)


class Status(str, Enum):
    HALLUCINATED_INVOKE = "llm_hallicunated_invoke"
    HALLUCINATED_RECURSION = "llm_hallicunated_recursion"
    COMPLETED = "completed"
    NO_LINKS = "no_links"


# Add langfuse and openai handler


class LinkPredictionAgentic:
    HALLUCINATIONS_MAX_RETRY = settings.HALLUCINATIONS_MAX_RETRY

    PROMPT_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|> Task: Identifying Foreign Keys Between Two Tables
You are tasked with identifying potential foreign key relationships between two tables based on the following criteria:
Context: You are in attempt {current_attempt}. Please consider the conditions outlined below before making a determination.

Conditions for Identifying Foreign Keys:
- Uniqueness Requirement: If a single pair of foreign keys are identified then uniqueness for atleast one of columns should be greater than 80%.
- Semantic Relationship: The column names in the two tables should have a logical and semantic relationship, or there should be logical and semantic relationship between column name and table names of links. For example, a column named order_id in the child table likely corresponds to order_id or a similar identifier in the parent table, and also column named order_id in shipping table is likely to correspond to a table named orders.
- Data Format and Data Type Consistency: The data format and pattern of values in the potential foreign key column should match the referenced column in the parent table. Ensure that the data types align (e.g., integers, alphanumeric) and that there is no significant mismatch in data format.
- created_date, modified_date or updated_date or any other columns indicating data entry updates should not be considered as foreign key.

Steps:
In attempts 1-3, you will attempt to identify foreign keys involving a single column in each table.
If, based on the provided metadata, no link is identified between the two tables, return 'NA' for column and table names

Input Structure:
Metadata Information for the Tables:
The metadata for each table will include:
count_distinct: The number of unique values in a column.
uniqueness: The percentage of distinct values to the total number of rows.
completeness: The percentage of non-null entries in the column.
datatype: The data type of the column (e.g., integer-Dimension, alphanumeric).
sample data: A few example values from the column.

{format_instructions}


If no valid link is identified, return:
'NA' for column and table names

Input: {previous_attempts} {table_info}

Based on your evaluation of the data and metadata, please proceed to attempt identifying the foreign key relationship by applying the conditions above. <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    LLM_CONFIG = {"temperature": 0.2}

    PROFILING_COLUMNS_REQUIRED = [
        "datatype",
        "distinct_count",
        "uniqueness",
        "completeness",
        "sample_data",
    ]

    def __init__(
        self,
        profiling_data: pd.DataFrame,
        primary_keys: Optional[list[tuple[str, str]]] = None,
        llm=None,
        *args,
        **kwargs,
    ):
        self.CACHE = {}

        self.llm = (
            ChatModelLLM.get_llm(
                model_name=settings.LLM_PROVIDER,
                llm_config=self.LLM_CONFIG,
            )
            if llm is None
            else llm
        )

        self.parser_linkages = JsonOutputParser(pydantic_object=linkage)

        self.prompt_link = PromptTemplate(
            template=self.PROMPT_TEMPLATE,
            input_variables=["current_attempt", "previous_attempts", "table_info"],
            partial_variables={"format_instructions": self.parser_linkages.get_format_instructions()},
        )

        self.link_identifier_llm = self.prompt_link | self.llm | self.parser_linkages

        self.profiling_data = preprocess_profiling_df(profiling_data)
        self.column_datatypes = read_column_datatypes(
            dtype=self.profiling_data[["table_name", "column_name", "datatype_l1"]]
        )

        self.primary_keys = primary_keys if primary_keys is not None else []

        self.table_ddl_statements = {
            table_name: generate_create_table_query(
                gbydata["column_name"].values.tolist(),
                table_name=table_name,
                profiling_data=gbydata,
                primary_keys=self.primary_keys,
                column_datatypes=self.column_datatypes,
                columns_required=self.PROFILING_COLUMNS_REQUIRED,
                mapping_dtypes_to_sql=True,
            )
            for (table_name,), gbydata in self.profiling_data.groupby(["table_name"])
        }

        self.graph = self.__workflow_builder__()

        self.status = None

        self.logs = []

    def link_identifier(self, state):
        """
        Identifies the link between tables
        Args:
            state (dict): The current graph state
        Returns:
            state (dict): New key added to state, Potential_Foreign_Key, that contains the link between two tables
        """

        log.info("---IDENTIFY LINK---")

        input_text = state["input_text"]
        iteration = state["iteration"]

        log_msg = "[*] TRYING TO IDENTIFY LINK BETWEEN: " + str(input_text)
        self.logs.append(log_msg)
        log.info(log_msg)

        if iteration is None:
            iteration = 0

        log_msg = f"[*] Iteration running: {iteration}"
        self.logs.append(log_msg)
        log.info(log_msg)

        if iteration == 0:
            error_msg = [""]
        else:
            error_msg = state["error_msg"]

        tab1, tab2 = input_text.split(" & ")
        table_details = self.table_ddl_statements[tab1] + "\n\n" + self.table_ddl_statements[tab2]

        if iteration == 0:
            current_attempt = 1

        else:
            current_attempt = iteration + 1

        previous_attempt_details = " ".join(error_msg)

        log_msg = f"[*] Message in previous attempt: {previous_attempt_details}"
        self.logs.append(log_msg)
        log.info(log_msg)

        try:
            potential_link = self.link_identifier_llm.invoke({
                "current_attempt": "Attempt " + str(current_attempt),
                "table_info": table_details,
                "previous_attempts": previous_attempt_details,
            })
        except Exception:
            log_msg = "[!] Killing LLM run due to halucinations in output"
            self.logs.append(log_msg)
            self.status = Status.HALLUCINATED_INVOKE
            log.info(log_msg)

            # log.info('[!] Killing LLM run due to halucinations in output')
            potential_link = {
                "table1": "NA",
                "column1": "NA",
                "table2": "NA",
                "column2": "NA",
            }
        iteration = current_attempt

        # Recursively search for the innermost dictionary
        potential_link_innermost_dict = extract_innermost_dict(potential_link)

        # checking for a possibility of recurcive loop in llm
        if iteration > 1:
            previous_potential_link = state["potential_link"]
            if previous_potential_link == potential_link_innermost_dict:
                log_msg = f"[!] Killing LLM run due to possibility of recurssion: {potential_link_innermost_dict}"
                self.status = Status.HALLUCINATED_RECURSION
                log.info(log_msg)
                self.logs.append(log_msg)
                potential_link_innermost_dict = {
                    "table1": "NA",
                    "column1": "NA",
                    "table2": "NA",
                    "column2": "NA",
                }
                return {
                    "potential_link": potential_link_innermost_dict,
                    "iteration": iteration,
                }

        log_msg = "[*] This is the link:" + str(potential_link_innermost_dict)
        log.info(log_msg)
        self.logs.append(log_msg)

        return {"potential_link": potential_link_innermost_dict, "iteration": iteration}

    def single_link_table_column_name_checker(self, state):
        """
        At least one of the columns in link should be unique

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New keys added to state, error_msg & if_error, error message is either table or column is missing and i_error would be True
        """
        # log.info("---CHECKING FOR TABLE & COLUMN NAME PRESENCE---")
        log_msg = "---CHECKING FOR TABLE & COLUMN NAME PRESENCE---"
        log.info(log_msg)
        self.logs.append(log_msg)

        potential_link = state["potential_link"]
        final_error_msg_list = state["error_msg"]
        log.info("chk1")
        # check if table names present
        stat_foreign_key = self.profiling_data.loc[self.profiling_data["table_name"] == potential_link["table1"]]

        if stat_foreign_key.shape[0] == 0:
            log.info("chk2")
            missing_table = potential_link["table1"]
            error_msg = f"{missing_table} seems to be missing. Check for any spelling errors in the table name."
            try:
                final_error_msg_list.append(error_msg)
            except Exception:
                final_error_msg_list = []
                final_error_msg_list.append(error_msg)
            # log.info(f"[!] {error_msg}")
            log_msg = f"[!] {error_msg}"
            log.info(log_msg)
            self.logs.append(log_msg)

            return {"error_msg": final_error_msg_list, "if_error": True}

        log.info("chk3")

        stat_foreign_key = stat_foreign_key.loc[stat_foreign_key["column_name"] == potential_link["column1"],]

        if stat_foreign_key.shape[0] == 0:
            log.info("chk4")
            table_name = potential_link["table1"]
            missing_column = potential_link["column1"]
            error_msg = (
                f"{missing_column} is not present in {table_name}. Check for any spelling errors in the column name."
            )
            try:
                final_error_msg_list.append(error_msg)
            except Exception:
                final_error_msg_list = []
                final_error_msg_list.append(error_msg)
            # log.info(f"[!] {error_msg}")
            log_msg = f"[!] {error_msg}"
            log.info(log_msg)
            self.logs.append(log_msg)

            return {"error_msg": final_error_msg_list, "if_error": True}

        # Referrenced table #########################3
        log.info("chk5")
        # check if table names present
        stat_referrence_key = self.profiling_data.loc[self.profiling_data["table_name"] == potential_link["table2"]]

        if stat_referrence_key.shape[0] == 0:
            log.info("chk6")
            missing_table = potential_link["table2"]
            error_msg = f"{missing_table} seems to be missing. Check for any spelling errors in the table name."
            try:
                final_error_msg_list.append(error_msg)
            except Exception:
                final_error_msg_list = []
                final_error_msg_list.append(error_msg)
            # log.info(error_msg)
            log_msg = f"[!] {error_msg}"
            log.info(log_msg)
            self.logs.append(log_msg)

            return {"error_msg": final_error_msg_list, "if_error": True}
        log.info("chk7")
        # check if column names present
        stat_referrence_key = stat_referrence_key.loc[stat_referrence_key["column_name"] == potential_link["column2"]]
        if stat_referrence_key.shape[0] == 0:
            log.info("chk8")
            table_name = potential_link["table2"]
            missing_column = potential_link["column2"]
            error_msg = (
                f"{missing_column} is not present in {table_name}. Check for any spelling errors in the column name."
            )
            try:
                final_error_msg_list.append(error_msg)
            except Exception:
                final_error_msg_list = []
                final_error_msg_list.append(error_msg)
            # log.info(error_msg)
            log_msg = f"[!] {error_msg}"
            log.info(log_msg)
            self.logs.append(log_msg)

            return {"error_msg": final_error_msg_list, "if_error": True}

        # If no error found
        log_msg = "[*] All Good No error found"
        self.logs.append(log_msg)
        log.info(log_msg)

        # log.info('All Good No error found')
        return {"if_error": False}

    def single_link_uniqueness_checker(self, state):
        """
        At least one of the columns in link should be unique

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New keys added to state, error_msg, error message if one of the column in the link is unique
        """
        # log.info("---CHECKING FOR COLUMN UNIQUENESS---")
        log_msg = "---CHECKING FOR COLUMN UNIQUENESS---"
        log.info(log_msg)
        self.logs.append(log_msg)

        potential_link = state["potential_link"]
        final_error_msg_list = state["error_msg"]

        # For Foreign & Referrenced key table ###########################
        stat_foreign_key = self.profiling_data.loc[
            (self.profiling_data["table_name"] == potential_link["table1"])
            & (self.profiling_data["column_name"] == potential_link["column1"]),
            ["uniqueness_ratio"],
        ]

        stat_referrence_key = self.profiling_data.loc[
            (self.profiling_data["table_name"] == potential_link["table2"])
            & (self.profiling_data["column_name"] == potential_link["column2"]),
            ["uniqueness_ratio"],
        ]

        # Calculate the max uniqueness for the foreign key table
        max_foreign_key_uniqueness = stat_foreign_key["uniqueness_ratio"].max()

        # Calculate the max uniqueness for the referenced key table
        max_referrenced_key_uniqueness = stat_referrence_key["uniqueness_ratio"].max()

        # Optionally, you can calculate the overall max uniqueness
        max_uniqueness = max(max_foreign_key_uniqueness, max_referrenced_key_uniqueness)

        if max_uniqueness >= settings.UNIQUENESS_THRESHOLD:
            # log.info('All Good No error found')
            log_msg = "All Good No error found"
            log.info(log_msg)
            self.logs.append(log_msg)

            return {"if_error": False}
        else:
            ref_column_uniqueness = max_referrenced_key_uniqueness
            ref_table_name = potential_link["table1"]
            ref_column = potential_link["column1"]
            foreign_table_name = potential_link["table2"]
            foreign_column = potential_link["column2"]
            foreign_column_uniqueness = max_foreign_key_uniqueness

            error_msg = f"Uniqueness of {foreign_column} column in table {foreign_table_name} is {foreign_column_uniqueness * 100:.2f} percent, while the uniqueness of {ref_column} in table {ref_table_name} is {ref_column_uniqueness * 100:.2f} percent. This is lower than the acceptable limit"
            try:
                final_error_msg_list.append(error_msg)
            except Exception:
                final_error_msg_list = []
                final_error_msg_list.append(error_msg)

            log_msg = f"[!] {error_msg}"
            log.info(log_msg)
            self.logs.append(log_msg)

            return {"error_msg": final_error_msg_list, "if_error": True}

    def single_link_datatype_checker(self, state):
        """
        Datatype of both columns should be same

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New keys added to state, error_msg, error message datatype of column are not similar
        """
        # log.info("---CHECKING FOR COLUMN UNIQUENESS---")
        log_msg = "---CHECKING FOR COLUMN UNIQUENESS---"
        log.info(log_msg)
        self.logs.append(log_msg)

        potential_link = state["potential_link"]
        final_error_msg_list = state["error_msg"]

        # For Foreign & Referrenced key table ###########################
        stat_foreign_key = self.profiling_data.loc[
            (self.profiling_data["table_name"] == potential_link["table1"])
            & (self.profiling_data["column_name"] == potential_link["column1"]),
            ["datatype_l1"],
        ]

        stat_referrence_key = self.profiling_data.loc[
            (self.profiling_data["table_name"] == potential_link["table2"])
            & (self.profiling_data["column_name"] == potential_link["column2"]),
            ["datatype_l1"],
        ]

        # Calculate the max uniqueness for the foreign key table

        foreign_key_datatype = stat_foreign_key["datatype_l1"].values[0]

        # Calculate the max uniqueness for the referenced key table

        referrenced_key_datatype = stat_referrence_key["datatype_l1"].values[0]

        if dtype_check(dtype1=foreign_key_datatype, dtype2=referrenced_key_datatype):
            # log.info('All Good No error found')
            log_msg = "All Good No error found"
            log.info(log_msg)
            self.logs.append(log_msg)

            return {"if_error": False}
        else:
            ref_table_name = potential_link["table1"]
            ref_column = potential_link["column1"]
            foreign_table_name = potential_link["table2"]
            foreign_column = potential_link["column2"]

            error_msg = f"Datatype of {foreign_column} column in table {foreign_table_name} is {foreign_key_datatype}, while the datatype of {ref_column} in table {ref_table_name} is {referrenced_key_datatype}. To join two columns dataype of both should be same"
            try:
                final_error_msg_list.append(error_msg)
            except Exception:
                final_error_msg_list = []
                final_error_msg_list.append(error_msg)

            log.info(error_msg)
            self.logs.append(f"[!] {error_msg}")

            return {"error_msg": final_error_msg_list, "if_error": True}

    def single_link_intersection_checker(self, state):
        """
        Checks intersection of values between columns

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New keys added to state, error_msg, error message if intersection between both the columns is low
        """
        log_msg = "---CHECKING FOR INTERSECTION BETWEEN COLUMNS---"
        log.info(log_msg)
        self.logs.append(log_msg)

        potential_link = state["potential_link"]
        final_error_msg_list = state["error_msg"]

        table1_name = potential_link["table1"]
        column1_name = potential_link["column1"]
        table2_name = potential_link["table2"]
        column2_name = potential_link["column2"]

        count_distinct_col1 = self.profiling_data.loc[
            (self.profiling_data.table_name == table1_name)
            & (self.profiling_data.column_name == column1_name)
        ]["distinct_count"].values[0]
        count_distinct_col2 = self.profiling_data.loc[
            (self.profiling_data.table_name == table2_name)
            & (self.profiling_data.column_name == column2_name)
        ]["distinct_count"].values[0]

        # Use adapter from one of the datasets to execute query
        adapter = self.table1.adapter

        try:
            intersect_count = adapter.intersect_count(
                table1=self.table1,
                column1_name=column1_name,
                table2=self.table2,
                column2_name=column2_name
            )
        except Exception as e:
            log.error(f"Error executing intersection query: {e}")
            error_msg = f"Could not calculate intersection between {table1_name}.{column1_name} and {table2_name}.{column2_name}."
            try:
                final_error_msg_list.append(error_msg)
            except AttributeError:
                final_error_msg_list = [error_msg]
            return {"error_msg": final_error_msg_list, "if_error": True}

        intersect_ratio_from_col = intersect_count / count_distinct_col1 if count_distinct_col1 > 0 else 0
        intersect_ratio_to_col = intersect_count / count_distinct_col2 if count_distinct_col2 > 0 else 0

        if intersect_count == 0:
            error_msg = f"The intersection between {column1_name} column in table {table1_name} with {column2_name} in table {table2_name} resulted in zero rows"
            try:
                final_error_msg_list.append(error_msg)
            except AttributeError:
                final_error_msg_list = [error_msg]
            log.info(error_msg)
            self.logs.append(error_msg)
            return {"error_msg": final_error_msg_list, "if_error": True}

        elif max(intersect_ratio_from_col, intersect_ratio_to_col) < settings.INTERSECT_RATIO_THRESHOLD:
            error_msg1 = f"Only {intersect_ratio_from_col * 100:.2f} percent of values in {column1_name} in table {table1_name} matched with {column2_name} in table {table2_name}. "
            error_msg2 = f"Only {intersect_ratio_to_col * 100:.2f} percent of values in {column2_name} in table {table2_name} matched with {column1_name} in table {table1_name}."
            error_msg = error_msg1 + error_msg2
            try:
                final_error_msg_list.append(error_msg)
            except AttributeError:
                final_error_msg_list = [error_msg]
            log.info(error_msg)
            self.logs.append(error_msg)
            return {"error_msg": final_error_msg_list, "if_error": True}
        else:
            log_msg = "All Good No error found"
            log.info(log_msg)
            self.logs.append(log_msg)
            return {
                "if_error": False,
                "intersect_count": intersect_count,
                "intersect_ratio_from_col": round(intersect_ratio_from_col, 3),
                "intersect_ratio_to_col": round(intersect_ratio_to_col, 3),
                "accuracy": round(max(intersect_ratio_from_col, intersect_ratio_to_col), 3),
            }

    def link_check_router(self, state):
        """
        Route the link checks

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, link_check_type, that contains the type of link which we need to check
        """
        # log.info("---IDENTIFY TYPE OF LINK---")
        log_msg = "---IDENTIFY TYPE OF LINK---"
        log.info(log_msg)
        self.logs.append(log_msg)

        potential_link = state["potential_link"]

        if potential_link["table1"] == "NA":
            link_type = "No_Link"
            if self.status is None:
                self.status = Status.NO_LINKS

        elif (len(potential_link) > 0) & (len(potential_link["table1"]) > 1):
            link_type = "Single_Link"
            self.status = Status.COMPLETED
        else:
            link_type = "Multiple_Link"
            self.status = Status.COMPLETED

        log_msg = f"Link type: {link_type}"
        log.info(log_msg)
        self.logs.append(log_msg)

        return link_type

    def error_checker(self, state):
        """
        Route to link identifier if error found

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, if_error, binary response for error present
        """
        log_msg = "---DID WE FIND ANY ERROR?---"
        log.info(log_msg)
        self.logs.append(log_msg)

        if_error = state["if_error"]
        if not if_error:
            error_found = "No"
        else:
            error_found = "Yes"
        log.info(error_found)
        return error_found

    def __workflow_builder__(self):
        log.info("[*] Compiling Agent Workflow Graph")

        from langgraph.graph import END, START, StateGraph

        from .utils import GraphState

        # Node adding
        workflow = StateGraph(GraphState)
        workflow.add_node("link_identifier", self.link_identifier)  # link identifier
        workflow.add_node(
            "single_link_table_column_name_checker",
            self.single_link_table_column_name_checker,
        )  # table column name checker
        workflow.add_node("single_link_uniqueness_checker", self.single_link_uniqueness_checker)  # uniqueness
        workflow.add_node("single_link_datatype_checker", self.single_link_datatype_checker)  # datatype
        workflow.add_node("single_link_intersection_checker", self.single_link_intersection_checker)

        # Adding edges
        workflow.add_edge(START, "link_identifier")

        workflow.add_conditional_edges(
            "link_identifier",
            self.link_check_router,
            {
                "Single_Link": "single_link_table_column_name_checker",
                "Multiple_Link": END,
                "No_Link": END,
            },
        )

        workflow.add_conditional_edges(
            "single_link_table_column_name_checker",
            self.error_checker,
            {
                "Yes": "link_identifier",
                "No": "single_link_uniqueness_checker",
            },
        )

        workflow.add_conditional_edges(
            "single_link_uniqueness_checker",
            self.error_checker,
            {
                "Yes": "link_identifier",
                "No": "single_link_datatype_checker",
            },
        )

        workflow.add_conditional_edges(
            "single_link_datatype_checker",
            self.error_checker,
            {
                "Yes": "link_identifier",
                "No": "single_link_intersection_checker",
            },
        )

        workflow.add_conditional_edges(
            "single_link_intersection_checker",
            self.error_checker,
            {
                "Yes": "link_identifier",
                "No": END,
            },
        )

        # Compile the workflow into a LangChain Runnable
        graph = workflow.compile()

        return graph

    def __post_processing__(self, data: pd.DataFrame) -> pd.DataFrame:
        def process(result: str):
            try:
                result = eval(result) if isinstance(result, str) else result
                return result if result["table1"] != "NA" else ""
            except Exception as ex:
                log.info(f"[!] Error while parsing: {ex}")
                return ""

        data["links"] = data.links.apply(process)
        res = data.links.tolist()
        res = list(filter(lambda x: not isinstance(x, str), res))
        res = pd.DataFrame(res)
        if res.shape[0] != 0:
            res.rename(
                columns={
                    "table1": "table1_name",
                    "column1": "column1_name",
                    "table2": "table2_name",
                    "column2": "column2_name",
                },
                inplace=True,
            )
        return res

    def __graph_invoke__(self, table1: DataSet, table2: DataSet) -> dict:
        self.table1 = table1
        self.table2 = table2
        final_output = {}
        final_output["table1"] = table1.name
        final_output["table2"] = table2.name

        start_time = time.time()
        input_message = HumanMessage(content=f"{table1.name} & {table2.name}")
        init_data = {
            "input_text": input_message.content,
            "iteration": None,
            "error_msg": [""],
        }

        try:
            event = {}
            for event in self.graph.stream(
                init_data,
                stream_mode="values",
                config={
                    "recursion_limit": 20,
                    "metadata": {"table_combo": tuple(sorted([table1.name, table2.name]))},
                },
            ):
                for key in [list(event.keys())[-1]]:
                    log.info(f"Finished running: {key}:")

        except GraphRecursionError as ex:
            log.warning(f"[!] Graph went into recursion loop when running for {table1.name} <=> {table2.name}")
            event["status"] = Status.HALLUCINATED_RECURSION
            event["potential_link"] = "NA"
            event["error_msg"] = ex

        except Exception as ex:
            import traceback
            log.error(f"[!] Error while running for {table1.name} <=> {table2.name}: Reason {traceback.format_exc()}")
            event["status"] = Status.HALLUCINATED_RECURSION
            event["potential_link"] = "NA"
            event["error_msg"] = ex
        # End time
        end_time = time.time()

        # Compute runtime
        runtime = end_time - start_time
        log.info(f"Runtime: {runtime:.2f} seconds")
        log.info(f"[*] link between tables: {event['potential_link']}")
        potential_link = event["potential_link"]

        if potential_link and potential_link.get("table1") != "NA":
            potential_link["intersect_count"] = event.get("intersect_count")
            potential_link["intersect_ratio_from_col"] = event.get("intersect_ratio_from_col")
            potential_link["intersect_ratio_to_col"] = event.get("intersect_ratio_to_col")
            potential_link["accuracy"] = event.get("accuracy")

        final_output["links"] = potential_link
        final_output["Runtime_secs"] = runtime
        # Logs monitoring
        final_output["logs"] = "\n".join(self.logs)
        final_output["status"] = self.status
        final_output["validation_logs"] = event["error_msg"]

        return final_output

    def __call__(self, assets: List[Tuple[DataSet]], *args, **kwds):
        results = []
        pb = tqdm(assets)
        for _, (table1, table2) in enumerate(pb):
            runs = 1
            pb.set_description(desc=f"[*] {table1.name} <==> {table2.name} Runs:{runs}")

            final_output = self.__graph_invoke__(table1, table2)

            # If status came out as Hallucinated retry one more time
            while (
                final_output["status"] in (Status.HALLUCINATED_INVOKE, Status.HALLUCINATED_RECURSION)
                and runs < self.HALLUCINATIONS_MAX_RETRY
            ):
                runs += 1
                log.info(f"[*] Hallucinated for {table1.name} <==> {table2.name} ... Retry no {runs} ")
                final_output = self.__graph_invoke__(table1=table1, table2=table2)

            results.append(final_output)
        return self.__post_processing__(data=pd.DataFrame(results)) if len(
            results
        ) != 0 else pd.DataFrame(), pd.DataFrame(results)
