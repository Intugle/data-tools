import logging
import re

import pandas as pd

from langchain.output_parsers import ResponseSchema
from langchain_core.prompts import PromptTemplate
from tqdm import tqdm

from intugle.core.llms.chat import ChatModelLLM
from intugle.core.settings import settings

log = logging.getLogger(__name__)


class KeyIdentificationLLM:
    KI_PROMPT_TEMPLATE = template = """Identify ONLY SINGLE primary key of a database table using profiling metadata of the schema.

- Review the provided metadata to determine which column is most likely the primary key in a database schema.
- The primary key should uniquely identify each record and usually has a unique constraint and no null values.

# Steps

1. **Examine Uniqueness**: Identify column that have a unique constraint or a high percentage of unique values compared to the total number of records.
2. **Check for Null Values**: Ensure the column considered for the primary key do not allow null values.
3. **DONOT Identify Combinations**: If no single column meets the criteria, then DONOT  identify multiple columns as composite key.
4. DONOT Identify Index Keys as a primary key ( They are usually integer type with, sequence of values that are increasing by 1 )
5. created_date, modified_date, updated_date should not be considered as primary key.

PROFILING_METADATA: {profiling_data}

INSTRUCTIONS: {format_instructions}"""

    primary_key = [ResponseSchema(name='PRIMARY KEY', description="Returns ONLY a SINGLE potential primary key."),]
    LLM_CONFIG = {
        "temperature": 1,
        # "model_kwargs":{
        "top_p": 0.5,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": "END",
        # }
    }

    def __init__(self, profiling_data: pd.DataFrame,
                 llm: ChatModelLLM = None,
                 *args, **kwargs):

        self.__chat_llm = ChatModelLLM.build(
            model_name=settings.LLM_PROVIDER,
            llm_config=self.LLM_CONFIG,
            prompt_template=PromptTemplate,
            template_string=self.KI_PROMPT_TEMPLATE,
            response_schemas=self.primary_key,
     

        ) if llm is None else llm

        self.profiling_data = profiling_data.loc[
            (profiling_data["uniqueness"] >= 0.8) & (profiling_data["datatype_l2"] == "dimension")
        ].reset_index(drop=True)[["table_name", "column_name", "count", "distinct_count", "null_count", "datatype_l1", "sample_data"]]

    @classmethod
    def fetch_primary_key(cls, llm: ChatModelLLM, profiling_data, table_name):
        response, parsing_success, prompt = llm.invoke(
            profiling_data=profiling_data,
            metadata={"table": table_name}
        )
        
        if parsing_success:
            return response["PRIMARY KEY"], prompt
        else:
            try:
                pattern = r'"PRIMARY KEY":\s*"(\w+)"'
                match = re.search(pattern, str(response))
                return match.group(1), prompt
            except Exception as ex:
                log.warning(f"[!] Error while parsing : {ex}")
                return "", prompt
                    
    def __format_profiling_data__(self, profiling_data: pd.DataFrame, table_name: str) -> str:
        
        profiling_txt = f"Table Name: {table_name}\n\n"

        temp = profiling_data[["column_name", "count", "distinct_count", "null_count", "datatype_l1", "sample_data"]]

        temp.rename(columns={"datatype_l1": "datatype"}, inplace=True)

        if temp.shape[0] == 0:

            return None
        
        profiling_txt += str(temp.to_dict(orient="records"))

        return profiling_txt
    
    def __run_ki__(self, table_name: str, prof_data: pd.DataFrame):

        profiling_txt = self.__format_profiling_data__(profiling_data=prof_data, table_name=table_name)

        primary_key = ""

        prompt = ""

        if prof_data is not None:
            
            primary_key, prompt = self.fetch_primary_key(llm=self.__chat_llm, profiling_data=profiling_txt, table_name=table_name)
            
            if primary_key not in prof_data["column_name"].values.tolist():
                
                log.warning(f"[!] {primary_key} key identified by LLM is not a valid column of {table_name} table")
                
                primary_key = ""

        return (table_name, prompt, primary_key)
    
    def __post_process__(self, ki_llm_result: pd.DataFrame) -> pd.DataFrame:
                
        ki_llm_result.fillna("", inplace=True)
        
        ki_llm_result = ki_llm_result[ki_llm_result.predicted_key_llm != ""].reset_index(drop=True)
        
        if (ki_llm_result.shape[0] <= 0):
            return None
        
        ki_llm_result["column_name"] = ki_llm_result["predicted_key_llm"]
        
        ki_llm_result["predicted_key_llm"] = 1
        
        ki_llm_result["predicted_key_prob_llm"] = settings.KI_CONFIG["RULES"]["LLM_PROBABILITY"]
        
        return ki_llm_result
    
    def __call__(self):
        
        ki_llm_result = pd.DataFrame()

        if self.profiling_data.shape[0] == 0:
            
            return ki_llm_result
        
        results = []

        pb = tqdm(self.profiling_data.groupby("table_name"))

        for (table_name), prof_data in pb:
            
            pb.set_description(desc=f"[*] {table_name}")
            
            pk_info = self.__run_ki__(table_name, prof_data)
            
            results.append(pk_info)
        
        ki_llm_result = pd.DataFrame(results, columns=["table_name", "prompt", "predicted_key_llm"])
        
        ki_llm_result = self.__post_process__(ki_llm_result=ki_llm_result)
        
        if ki_llm_result is not None and not ki_llm_result.empty:
            return ki_llm_result.iloc[0].to_dict()
        return {}
