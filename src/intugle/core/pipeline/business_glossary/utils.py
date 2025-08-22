import logging
import re

import pandas as pd

from langchain.output_parsers import RetryOutputParser
from langchain_core.prompt_values import StringPromptValue

from intugle.core import settings
from intugle.core.utilities.processing import preprocess_profiling_data

log = logging.getLogger(__name__)


def llm_based_reparsing(retry_output_parser: RetryOutputParser, bad_response: str, prompt: StringPromptValue | str):
    prompt_value = prompt if isinstance(prompt, StringPromptValue) else StringPromptValue(text=prompt)
    response = retry_output_parser.parse_with_prompt(bad_response, prompt_value)
    return response


def manual_parsing(keys_name: list, text: str, **kwargs):
    log.warning(f"[!] Langchain parser failed to parse ==> {text} ... trying manual_parsing parsing")
    for key_name in keys_name:
        pattern = r'"{}":\s*"(.*?)"'.format(key_name)
        try:
            match = re.search(pattern, text)
            _term = match.group(1)
            return _term
        except Exception:
            ...
    retry_output_parser = kwargs.get("retry_output_parser", None)
    if retry_output_parser is not None:
        log.warning("[!] Failed manual parsing also .. trying llm parsing")
        try:
            response = llm_based_reparsing(
                retry_output_parser=kwargs.get("retry_output_parser"), bad_response=text, prompt=kwargs.get("prompt")
            )
            return response[keys_name[0]]
        except Exception:
            log.warning("[!] Failed llm parsing also")

    return []


def get_additional_context(table_name: str, global_additional_context: str = "", additional_table_context: str = ""):
    # fetch
    consolidated_additional_context = []

    if len(global_additional_context) != 0:
        consolidated_additional_context.append(f"- {global_additional_context}")

    if len(additional_table_context) != 0:
        consolidated_additional_context.append(f"- `{table_name}` context:  {additional_table_context}")

    return "\n".join(consolidated_additional_context)


def preprocess_profiling_df(profiling_data: pd.DataFrame):

    profiling_data = preprocess_profiling_data(
        profiling_data=profiling_data,
        sample_limit=settings.STRATA_SAMPLE_LIMIT,
        dtypes_to_filter=None
    )

    return profiling_data
