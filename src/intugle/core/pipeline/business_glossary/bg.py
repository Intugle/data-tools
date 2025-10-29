
import json
import logging
import re
import time

import pandas as pd

from langchain_core.prompts import PromptTemplate
from tqdm import tqdm

from intugle.core import settings
from intugle.core.llms.chat import ChatModelLLM
from intugle.core.utilities.llm_utils import generate_create_table_query, read_column_datatypes

from .prompts import (
    BUSINESS_GLOSSARY_PROMPTS,
    column_glossary,
    column_tag_glossary,
    table_glossary,
)
from .utils import (
    get_additional_context,
    manual_parsing,
    preprocess_profiling_df,
)

log = logging.getLogger(__name__)

tqdm.pandas()
line_count = settings.BG_CONFIG["THRESHOLD"]["LINE_COUNT"]
word_count = settings.BG_CONFIG["THRESHOLD"]["WORD_COUNT"]


TABLE_DESCRIPTION = settings.BG_CONFIG["GLOSSARY_GEN"]["TABLE_DESCRIPTION"]
COLUMN_GLOSSARY = settings.BG_CONFIG["GLOSSARY_GEN"]["COLUMN_GLOSSARY"]
COLUMN_TECHNICAL_GLOSSARY = settings.BG_CONFIG["GLOSSARY_GEN"]["COLUMN_TECHNICAL_GLOSSARY"]
BUSINESS_TAGS = settings.BG_CONFIG["GLOSSARY_GEN"]["BUSINESS_TAGS"]
USE_COLUMN_CONTEXT = settings.BG_CONFIG["GLOSSARY_GEN"]["USE_COLUMN_CONTEXT"]


def raw_json_parser(regex: str, data: str):
    match = re.search(regex, data, re.DOTALL)

    if match:
        inner_dict_str = match.group(1)
        inner_dict = json.loads(inner_dict_str)
        return inner_dict
    else:
        log.error(f"[!] Couldnot parse raw llm json : {data}")
        return ""


class BusinessGlossary:
    MAX_REGEX_RETRIES = 1

    TEMPLATE_NAME = "gpt-4o-mini"

    LLM_GLOSSARY_CONFIG = {
        "temperature": 0.6,
    }

    LLM_TAG_CONFIG = {
        "temperature": 0.4,
    }

    def __init__(self, profiling_data: pd.DataFrame, *args, **kwargs):

        profiling_data = preprocess_profiling_df(profiling_data.copy())
        self.profiling_data = profiling_data[
            [
                "table_name",
                "column_name",
                "sample_data",
                "datatype_l1",
            ]
        ]

        self.column_datatypes = (
            read_column_datatypes(
                dtype=self.profiling_data[
                    ["table_name", "column_name", "datatype_l1"]
                ].reset_index(drop=True)
            )
            if settings.BG_CONFIG["INCLUDE_DTYPES"]
            else {}
        )

        self.__table_glossary_llm = ChatModelLLM.build(
            model_name=settings.LLM_PROVIDER,
            llm_config=self.LLM_GLOSSARY_CONFIG,
            response_schemas=table_glossary,
            template_string=BUSINESS_GLOSSARY_PROMPTS[self.TEMPLATE_NAME][
                "TABLE_GLOSSARY_TEMPLATE"
            ],
            prompt_template=PromptTemplate,
        )

        self.__business_glossary_llm = ChatModelLLM.build(
            model_name=settings.LLM_PROVIDER,
            llm_config=self.LLM_GLOSSARY_CONFIG,
            response_schemas=column_glossary,
            template_string=BUSINESS_GLOSSARY_PROMPTS[self.TEMPLATE_NAME][
                "BUSINESS_GLOSSARY_TEMPLATE"
            ],
            prompt_template=PromptTemplate,
        )
        self.__business_tags_llm = ChatModelLLM.build(
            model_name=settings.LLM_PROVIDER,
            llm_config=self.LLM_TAG_CONFIG,
            response_schemas=column_tag_glossary,
            template_string=BUSINESS_GLOSSARY_PROMPTS[self.TEMPLATE_NAME][
                "BUSINESS_TAGS_TEMPLATE"
            ],
            prompt_template=PromptTemplate,
        )

        self.global_additional_context: str = kwargs.get(
            "global_additional_context", ""
        )
        self.table_additional_contexts: dict = kwargs.get(
            "table_additional_contexts", {}
        )

    @classmethod
    def fetch_table_glossary(
        cls,
        llm: ChatModelLLM,
        sql_statements: str,
        domain: str,
        table_name: str = "",
        additional_context: str = "",
    ):
        response, parsing_success, raw_response = llm.invoke(
            create_statements=sql_statements,
            domain=domain,
            table=table_name,
            additional_context=additional_context,
            metadata={
                "type": "table glossary",
                "table": table_name,
            },
        )

        if parsing_success:
            try:
                return response["table_glossary"], raw_response
            except Exception:
                response = raw_response

        result = manual_parsing(
            keys_name=["table_glossary", table_name],
            text=response,
        )
        return result, raw_response

    @classmethod
    def fetch_column_glossary(
        cls,
        llm: ChatModelLLM,
        sql_statements: str,
        domain: str,
        table_name: str,
        column_name: str,
        additional_context: str = "",
    ):
        # format_output = """
        # # Output the business glossary in the following structure:
        # ```json
        #     "column_glossary": { 
        #         "column_name_1": "A brief description of the purpose or role of column_name_1."},
        #         "column_name_2": "A brief description of the purpose or role of column_name_2."}
        #     }
        # ```        
        # """
        response, parsing_success, raw_response = llm.invoke(
            create_statements=sql_statements,
            domain=domain,
            column=column_name,
            additional_context=additional_context,
            metadata={
                "type": "column glossary",
                "column": f"{table_name}.{column_name}",
            },
        )

        if parsing_success:
            try:
                return response["column_glossary"], raw_response
            except Exception:
                response = raw_response

        result = manual_parsing(
            keys_name=["column_glossary", column_name], text=response
        )
        return result, raw_response

    @classmethod
    def fetch_business_tags(
        cls,
        llm: ChatModelLLM,
        sql_statements: str,
        domain: str,
        table_name: str,
        column_name: str,
        additional_context: str = "",
    ):
        # format_output = """
        #     # Output the tags in the following structure:
        #     ```json
        #     "column_tag_glossary":{
        #         "column_name": ["Tag1", "Tag2", "Tag3"],
        #         }
        #     ```
        # """
        response, parsing_success, raw_response = llm.invoke(
            create_statements=sql_statements,
            domain=domain,
            column=column_name,
            additional_context=additional_context,
            metadata={"type": "column tags", "column": f"{table_name}.{column_name}"},
        )

        if parsing_success:
            try:
                return response["column_tag_glossary"], raw_response
            except Exception:
                response = raw_response

        result = manual_parsing(
            keys_name=["column_tag_glossary", column_name], text=response
        )

        return result, raw_response

    def bg_tg(self, row, profiling_temp, domain, additional_context: str = ""):
        column = row["column_name"]
        table_name = row["table_name"]
        sql_statements_2 = generate_create_table_query(
            table_columns=[column],
            column_datatypes=self.column_datatypes,
            table_name=table_name,
            profiling_data=profiling_temp,
            columns_required=["sample_data"],
        )

        glossary, _ = self.fetch_column_glossary(
            llm=self.__business_glossary_llm,
            sql_statements=sql_statements_2,
            domain=domain,
            column_name=column,
            table_name=table_name,
            additional_context=additional_context,
        )
        tags, _ = self.fetch_business_tags(
            llm=self.__business_tags_llm,
            sql_statements=sql_statements_2,
            domain=domain,
            column_name=column,
            table_name=table_name,
            additional_context=additional_context,
        )

        # ()
        return pd.Series([glossary, tags], index=["business_glossary", "business_tags"])

    def __run_bg__(self, table_name: str, domain: str):
        st = time.time()

        # for table_name,profiling_temp in self.profiling_data.groupby(["table_name"]):
        sql_statements = generate_create_table_query(
            table_columns=self.profiling_data.column_name.tolist(),
            column_datatypes=self.column_datatypes,
            table_name=table_name,
            profiling_data=self.profiling_data,
            columns_required=["sample_data"],
        )

        additional_context_to_llm = get_additional_context(
            table_name=table_name,
            global_additional_context=self.global_additional_context,
            additional_table_context=self.table_additional_contexts.get(
                str(table_name), ""
            ),
        )

        table_glossary, _ = self.fetch_table_glossary(
            llm=self.__table_glossary_llm,
            sql_statements=sql_statements,
            domain=domain,
            table_name=table_name,
            additional_context=additional_context_to_llm,
        )
        # ()

        self.profiling_data.loc[
            self.profiling_data.index, ["business_glossary", "business_tags"]
        ] = self.profiling_data.progress_apply(
            self.bg_tg,
            axis=1,
            profiling_temp=self.profiling_data,
            domain=domain,
            additional_context=additional_context_to_llm,
        )
        self.profiling_data.loc[self.profiling_data.index, "table_glossary"] = table_glossary
        end = time.time()
        self.profiling_data.loc[self.profiling_data.index, "execution_time"] = (
            f"{end - st:.2f}"
        )
        return table_glossary, self.profiling_data

    def __call__(self, table_name: str, domain: str):
        table_glossary, glossary_df = self.__run_bg__(table_name, domain=domain)
        return table_glossary, glossary_df
