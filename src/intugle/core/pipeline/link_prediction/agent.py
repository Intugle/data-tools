import logging
import time

from enum import Enum

import pandas as pd

from langchain.output_parsers import OutputFixingParser
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.core.llms.chat import ChatModelLLM
from intugle.core.observability import get_langfuse_handler
from intugle.core.pipeline.link_prediction.prompt import link_identification_agent_prompt
from intugle.core.pipeline.link_prediction.schemas import GraphState, Link
from intugle.core.pipeline.link_prediction.tools import LinkPredictionTools
from intugle.core.pipeline.link_prediction.utils import prepare_ddl_statements, preprocess_profiling_df

log = logging.getLogger(__name__)


class Status(str, Enum):
    HALLUCINATED_INVOKE = "llm_hallicunated_invoke"
    HALLUCINATED_RECURSION = "llm_hallicunated_recursion"
    COMPLETED = "completed"
    NO_LINKS = "no_links"


class MultiLinkPredictionAgent:
    HALLUCINATIONS_MAX_RETRY = settings.HALLUCINATIONS_MAX_RETRY

    LLM_CONFIG = {"temperature": 0.2}

    PROFILING_COLUMNS_REQUIRED = [
        "glossary",
        "datatype_l1",
        "distinct_value_count",
        "uniqueness_ratio",
        "completeness_ratio",
        "sample_data",
    ]

    def __init__(
        self,
        table1_dataset: DataSet,
        table2_dataset: DataSet,
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

        pydantic_parser = PydanticOutputParser(pydantic_object=Link)
        self.parser_linkages = OutputFixingParser.from_llm(
            llm=self.llm, parser=pydantic_parser
        )

        self.link_identification_agent_prompt = link_identification_agent_prompt

        self.table1_dataset = table1_dataset
        self.table2_dataset = table2_dataset

        profiling_data = pd.concat(
            [table1_dataset.profiling_df, table2_dataset.profiling_df], ignore_index=True
        )
        profiling_data.rename(columns={
            "column_name": "upstream_column_name",
            "table_name": "upstream_table_name",
            "distinct_count": "distinct_value_count",
            "predicted_datatype_l1": "datatype_l1",
            "predicted_datatype_l2": "datatype_l2",
            "business_glossary": "glossary",
        }, inplace=True)

        self.profiling_data = preprocess_profiling_df(profiling_data)

        self.table_ddl_statements = {
            **prepare_ddl_statements(table1_dataset),
            **prepare_ddl_statements(table2_dataset),
        }

        self.lpt = LinkPredictionTools(
            profiling_data=self.profiling_data,
            datasets={
                self.table1_dataset.name: self.table1_dataset,
                self.table2_dataset.name: self.table2_dataset,
            },
            adapter=self.table1_dataset.adapter,
        )

        self.agent = create_react_agent(
            model=self.llm,
            tools=self.lpt.get_tools(),
            prompt=self.link_identification_agent_prompt,
            state_schema=GraphState,
        )

        self.status = None
        self.logs = []

    def __graph_invoke__(self) -> dict:
        final_output = {}
        final_output["table1"] = self.table1_dataset.name
        final_output["table2"] = self.table2_dataset.name

        start_time = time.time()
        HumanMessage(content=f"{self.table1_dataset.name} & {self.table2_dataset.name}")
        init_data = {
            "messages": [("user", f"### Table Schemas:\n```sql\n{self.table_ddl_statements[self.table1_dataset.name]}\n```\n```sql\n{self.table_ddl_statements[self.table2_dataset.name]}\n```")],
            "table1_name": self.table1_dataset.name,
            "table2_name": self.table2_dataset.name,
            "remaining_steps": 25,  # This is for the prebuilt agent, not directly used in our custom graph
        }

        # Get Langfuse handler if enabled
        langfuse_handler = get_langfuse_handler(trace_name=f"lp-id-{self.table1_dataset.name}-{self.table2_dataset.name}")
        config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}

        try:
            event = {}
            for event in self.agent.stream(
                init_data,
                stream_mode="values",
                config={
                    "recursion_limit": 20,
                    "metadata": {"table_combo": tuple(sorted([self.table1_dataset.name, self.table2_dataset.name]))},
                    **config,
                },
            ):
                for key in [list(event.keys())[-1]]:
                    log.info(f"Finished running: {key}:")

        except GraphRecursionError as ex:
            log.warning(f"[!] Graph went into recursion loop when running for {self.table1_dataset.name} <=> {self.table2_dataset.name}")
            event["status"] = Status.HALLUCINATED_RECURSION
            event["potential_link"] = "NA"
            event["error_msg"] = str(ex)

        except Exception as ex:
            import traceback
            log.error(f"[!] Error while running for {self.table1_dataset.name} <=> {self.table2_dataset.name}: Reason {traceback.format_exc()}")
            event["status"] = Status.HALLUCINATED_RECURSION
            event["potential_link"] = "NA"
            event["error_msg"] = str(ex)

        end_time = time.time()
        runtime = end_time - start_time
        log.info(f"Runtime: {runtime:.2f} seconds")

        # Extract links from the lpt._links dictionary
        potential_links_for_pair = self.lpt._links.get((self.table1_dataset.name, self.table2_dataset.name), {})
        
        # Convert OutputSchema objects to dictionaries
        links_data = [link.model_dump() for link in potential_links_for_pair.values()]

        final_output["links"] = links_data
        final_output["Runtime_secs"] = runtime
        final_output["logs"] = "\n".join(self.logs)  # Agent logs are not directly captured here yet
        final_output["status"] = self.status  # This status needs to be set by the agent
        final_output["validation_logs"] = event.get("error_msg", "")

        return final_output

    def __call__(self, *args, **kwds):
        runs = 1
        final_output = self.__graph_invoke__()

        while (
            final_output["status"] in (Status.HALLUCINATED_INVOKE, Status.HALLUCINATED_RECURSION)
            and runs < self.HALLUCINATIONS_MAX_RETRY
        ):
            runs += 1
            log.info(f"[*] Hallucinated for {self.table1_dataset.name} <==> {self.table2_dataset.name} ... Retry no {runs} ")
            final_output = self.__graph_invoke__()

        return final_output
