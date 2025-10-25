import logging
import os

import pandas as pd

from langchain_community.callbacks import get_openai_callback

from intugle.core import settings
from intugle.core.conceptual_search.agent.initializer import (
    data_product_builder_agent,
    data_product_planner_agent,
)
from intugle.core.conceptual_search.agent.retrievers import ConceptualSearchRetrievers
from intugle.core.conceptual_search.agent.tools.tool_builder import (
    DataProductBuilderAgentTools,
    DataProductPlannerAgentTools,
)
from intugle.core.conceptual_search.graph_based_column_search.networkx_initializers import (
    prepare_networkx_graph as prepare_column_networkx_graph,
)
from intugle.core.conceptual_search.graph_based_table_search.networkx_initializers import (
    prepare_networkx_graph as prepare_table_networkx_graph,
)
from intugle.core.conceptual_search.utils import batched
from intugle.core.llms.chat import ChatModelLLM
from intugle.parser.manifest import Manifest, ManifestLoader

log = logging.getLogger(__name__)


class ConceptualSearch:
    def __init__(self):
        log.info("Initializing ConceptualSearch...")
        self.manifest = self._load_manifest()
        self._initialize_graphs()
        self.retriever = ConceptualSearchRetrievers()

        self.llm = ChatModelLLM.get_llm(
            model_name=settings.LLM_PROVIDER,
            llm_config={"temperature": 0.05},
        )

        self._data_product_planner_tool = DataProductPlannerAgentTools(
            retrieval_tool=self.retriever
        )
        self._data_product_builder_tool = DataProductBuilderAgentTools(
            retrieval_tool=self.retriever, manifest=self.manifest
        )

        self._data_product_planner_agent = data_product_planner_agent(
            llm=self.llm, tools=self._data_product_planner_tool.list_tools()
        )
        self._data_product_builder_agent = data_product_builder_agent(
            llm=self.llm, tools=self._data_product_builder_tool.list_tools()
        )

    def _load_manifest(self) -> Manifest:
        log.info(f"Loading manifest from project base: {settings.PROJECT_BASE}")
        manifest_loader = ManifestLoader(settings.PROJECT_BASE)
        manifest_loader.load()
        return manifest_loader.manifest

    def _initialize_graphs(self):
        log.info("Initializing conceptual search graphs...")
        prepare_table_networkx_graph(self.manifest)
        prepare_column_networkx_graph(self.manifest)
        log.info("Conceptual search graphs initialized.")

    def generate_data_product(self, attributes_df: pd.DataFrame):
        BATCH_SIZE = 2

        if attributes_df.shape[0] <= 0:
            raise ValueError("Empty data product plan")

        total_records = attributes_df.shape[0]
        log.info(f"🚀 Starting processing of {total_records} attributes...")

        cost = 0
        for b in batched(attributes_df, BATCH_SIZE):
            messages = [
                {
                    "messages": [
                        (
                            "user",
                            f"attribute_name: {row['Attribute Name']} \n\n attribute_description: {row['Attribute Description']} \n\n attribute_type: {row['Attribute Classification']}",
                        )
                    ]
                }
                for _, row in b.iterrows()
            ]

            with get_openai_callback() as cb:
                self._data_product_builder_agent.batch(messages)
                cost += cb.total_cost

        dp = pd.read_csv("column_logic_results.csv")
        dp["source"] = dp["table_name"] + "$$##$$" + dp["column_name"]
        return dp, cost

    def generate_data_product_plan(self, query: str, additional_context: str = None):
        if additional_context and additional_context.strip():
            query += f"\nAdditional Context:\n{additional_context}"

        total_cost = 0.0
        with get_openai_callback() as cb:
            self._data_product_planner_agent.invoke(
                input={"messages": [("user", query)]},
            )
            total_cost = cb.total_cost

        if os.path.exists("attributes.csv"):
            return pd.read_csv("attributes.csv"), total_cost

        return None, None
