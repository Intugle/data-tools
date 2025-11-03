import logging
import os

import pandas as pd

from langchain_core.runnables import chain

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
from intugle.core.conceptual_search.plan import DataProductPlan
from intugle.core.conceptual_search.utils import (
    batched,
    langfuse_callback_handler,
)
from intugle.core.llms.chat import ChatModelLLM
from intugle.libs.smart_query_generator import (
    CategoryType,
    ETLModel,
    FieldsModel,
)
from intugle.parser.manifest import Manifest, ManifestLoader

log = logging.getLogger(__name__)


class ConceptualSearch:
    def __init__(self, force_recreate=False):
        log.info("Initializing ConceptualSearch...")
        self.manifest = self._load_manifest()
        self._initialize_graphs(force_recreate=force_recreate)
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
        handler = langfuse_callback_handler()
        self.callbacks = [handler] if handler else []

    def _load_manifest(self) -> Manifest:
        log.info(f"Loading manifest from project base: {settings.PROJECT_BASE}")
        manifest_loader = ManifestLoader(settings.PROJECT_BASE)
        manifest_loader.load()
        return manifest_loader.manifest

    def _initialize_graphs(self, force_recreate=False):
        log.info("Initializing conceptual search graphs...")
        prepare_table_networkx_graph(self.manifest, force_recreate)
        prepare_column_networkx_graph(self.manifest, force_recreate)
        log.info("Conceptual search graphs initialized.")

    async def generate_data_product(
        self, plan: DataProductPlan | pd.DataFrame
    ) -> ETLModel:
        if isinstance(plan, DataProductPlan):
            attributes_df = plan.to_df()
            product_name = plan.name
        elif isinstance(plan, pd.DataFrame):
            attributes_df = plan
            product_name = attributes_df["Data Product Name"].iloc[0]
        else:
            raise TypeError("plan must be either a DataProductPlan or a pandas DataFrame.")

        BATCH_SIZE = 2

        if attributes_df.shape[0] <= 0:
            raise ValueError("Empty data product plan")

        # Clear previous results before starting
        self._data_product_builder_tool.column_logic_results = []

        total_records = attributes_df.shape[0]
        log.info(f"Starting processing of {total_records} attributes...")

        for b in batched(attributes_df, BATCH_SIZE):
            messages = [
                {
                    "messages": [
                        (
                            "user",
                            f"attribute_name: {row['Attribute Name']} \n\n attribute_description: {row['Attribute Description']} \n\n attribute_classification: {row['Attribute Classification']}",
                        )
                    ]
                }
                for _, row in b.iterrows()
            ]

            @chain
            async def run(inputs: dict):
                await self._data_product_builder_agent.abatch(inputs["messages"])

            await run.ainvoke(
                {"messages": messages},
                config={
                    "callbacks": self.callbacks,
                    "run_name": "Data Product Building",
                },
            )

        # Construct ETLModel from in-memory results
        fields = []
        mapped_attributes = self._data_product_builder_tool.column_logic_results

        # Create a lookup for all columns in the manifest to get their IDs
        column_id_map = {
            f"{source.table.name}.{column.name}": f"{source.table.name}.{column.name}"
            for source in self.manifest.sources.values()
            for column in source.table.columns
        }

        for attr in mapped_attributes:
            if not attr.table_name or not attr.column_name:
                log.warning(
                    f"Could not map attribute '{attr.attribute_name}', skipping."
                )
                continue

            column_id_key = f"{attr.table_name}.{attr.column_name}"
            column_id = column_id_map.get(column_id_key)

            if not column_id:
                log.warning(
                    f"Could not find ID for column '{column_id_key}' for attribute '{attr.attribute_name}', skipping."
                )
                continue

            field = FieldsModel(
                id=column_id,
                name=attr.attribute_name,
                category=attr.attribute_classification,
            )

            if attr.attribute_classification == CategoryType.measure:
                if not attr.measure_func:
                    log.warning(
                        f"Measure '{attr.attribute_name}' is missing a measure_func, defaulting to 'count'."
                    )
                    field.measure_func = "count"
                else:
                    field.measure_func = attr.measure_func

            fields.append(field)

        return ETLModel(name=product_name, fields=fields)

    async def generate_data_product_plan(
        self,
        query: str,
        additional_context: str = None,
        use_cache: bool = False,
    ) -> DataProductPlan | None:
        if use_cache and os.path.exists("attributes.csv"):
            log.info("Loading data product plan from attributes.csv (cache).")
            return DataProductPlan(pd.read_csv("attributes.csv"))

        log.info("Generating new data product plan...")
        self._data_product_planner_tool.generated_plan = (
            None  # Clear previous plan
        )

        if additional_context and additional_context.strip():
            query += f"\nAdditional Context:\n{additional_context}"

        await self._data_product_planner_agent.ainvoke(
            input={"messages": [("user", query)]},
            config={
                "callbacks": self.callbacks,
                "metadata": {"Query": query},
                "run_name": "Data product planning",
            },
        )

        if self._data_product_planner_tool.generated_plan is not None:
            return DataProductPlan(
                self._data_product_planner_tool.generated_plan
            )

        return None
