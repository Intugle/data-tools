# ====================================================================
#  Importing the required python packages
# ====================================================================

# from core.conf import
import logging
import re

import pandas as pd

from langchain.output_parsers import ResponseSchema
from tqdm.auto import tqdm

from intugle.core.llms.chat import ChatModelLLM
from intugle.core.settings import settings
from intugle.core.utilities.processing import adjust_sample

log = logging.getLogger(__name__)

tqdm.pandas()


LLM_SAMPLE_SIZE = settings.DI_CONFIG["L2PARAMS"]["LLM_SAMPLE_SIZE"]


class L2ModelLLM:
    """
    L2 model is mainly responsible for classifying:
    - the integer and float datatype into integer_measure or
    - integer_dimension and same for float.
    - this model also finds the specific format the date & time datatype lies in (e.g. YYYY:MM:DD , YYYY-MM-DD, YYYY:MM:DD H:m:s , etc...)
    - this model uses llm for dimension & measure classification and a regex based approach for the date & time classification.
    """

    DIM_MEASURE_PROMPT = """Class Category
    - Dimensions contain qualitative information. These are descriptive attributes, like a product category, product key, customer address, or country. Dimensions can contain numeric characters (like an alphanumeric customer ID), but are not numeric values (It wouldn’t make sense to add up all the ID numbers in a column, for example).
    - Measures contain quantitative values that you can measure. Measures can be aggregated.
    Please analyze the table and classify column as either a 'Measure' or a 'Dimension' or 'Unknown'.
    INPUT
    ### TABLE:\n{table}\n\n 
    ### COLUMN NAME: {column_name}\n
    ### CLASS CATEGORY:{format_instructions}
    """
    dm_class_schema = [
        ResponseSchema(
            name="DM_class",
            description="This final class of a column Dimension, Measure & Unknown",
        )
    ]

    LLM_CONFIG = {"temperature": 0.0}

    def __init__(self, *args, **kwargs):
        # langfuse for monitoring

        self.chat_llm = ChatModelLLM.build(
            model_name=settings.LLM_PROVIDER,
            llm_config=self.LLM_CONFIG,
            template_string=self.DIM_MEASURE_PROMPT,
            response_schemas=self.dm_class_schema,
        )

        self.table_dict = {}

    def __classify_dim_measure__(self, table: str, column_name: str) -> str:
        response, parsing_success, _ = self.chat_llm.invoke(
            table=table,
            column_name=column_name,
            metadata={"column": f"{table}.{column_name}"},
        )

        if parsing_success:
            return response["DM_class"]
        else:
            try:
                pattern = re.compile(r'"DM_class":\s+"(Dimension|Measure|Unknown)"')
                return re.findall(pattern, response)[-1]
            except Exception as ex:
                log.error(f"[!] Error while parsing: {ex}")
                return "Unknown"

    def __call__(self, row) -> str:
        column_name = row["column_name"]

        sample_data = adjust_sample(
            sample_data=row["sample_data"], expected_size=settings.L2_SAMPLE_LIMIT
        )

        table = pd.DataFrame(sample_data, columns=[column_name])

        value = self.__classify_dim_measure__(table=str(table), column_name=column_name)

        return value.lower()


class L2Model:
    def __init__(self, *args, **kwargs):
        self.__model = L2ModelLLM(*args, **kwargs)

    def __call__(
        self,
        l1_pred: pd.DataFrame,
    ):

        l1_pred["predicted_datatype_l2"] = l1_pred.progress_apply(
            self.__model,
            axis=1,
        )

        return l1_pred
