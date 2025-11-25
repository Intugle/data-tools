import logging

from typing import TYPE_CHECKING, Optional

from langchain.chat_models import init_chat_model
from langchain.output_parsers import (
    ResponseSchema,
    RetryWithErrorOutputParser,
    StructuredOutputParser,
)
from langchain.prompts import BaseChatPromptTemplate, ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter

from intugle.core import settings

log = logging.getLogger(__name__)


if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel


class ChatModelLLM:
    """
    A Wrapper around Chat LLM to invoke on any of the pipeline that uses llm
    """

    # number of retries to the LLM.
    MAX_RETRIES = settings.MAX_RETRIES

    def __init__(
        self,
        model_name: Optional[str] = None,
        response_schemas: list[ResponseSchema] = None,
        output_parser=StructuredOutputParser,
        prompt_template=ChatPromptTemplate,
        template_string: str = None,
        config: dict = {},
        *args,
        **kwargs,
    ):
        if settings.CUSTOM_LLM_INSTANCE:
            self.model: "BaseChatModel" = settings.CUSTOM_LLM_INSTANCE
        elif model_name:
            self.model: "BaseChatModel" = init_chat_model(
                model_name, max_retries=self.MAX_RETRIES, rate_limiter=self._get_rate_limiter(), **config
            )
        else:
            raise ValueError("Either 'settings.CUSTOM_LLM_INSTANCE' must be set or 'LLM_PROVIDER' must be provided.")

        self.parser: StructuredOutputParser = output_parser  # the output parser

        self.prompt_template: BaseChatPromptTemplate = prompt_template  # prompt template

        self.output_parser = (
            self.__output_parser_builder__(response_schemas=response_schemas)
            if response_schemas is not None
            else None
        )  # the built output parser

        self.format_instructions = (
            self.output_parser.get_format_instructions() if self.output_parser is not None else None
        )  # the format instructions

        self.llm_prompt = self.prompt_template.from_template(
            template=template_string
        )  # get the final builded prompt template

    def chat(self, msg):
        return self.model.invoke(msg).content

    def __output_parser_builder__(self, response_schemas: list[ResponseSchema] = None):
        """
        for building the corresponding output paraser from the given ResponseSchema
        """
        parser = self.parser.from_response_schemas(response_schemas=response_schemas)
        retry_parser = RetryWithErrorOutputParser.from_llm(
            parser=parser, llm=self.model, max_retries=self.MAX_RETRIES
        )
        return retry_parser

    @classmethod
    def _get_rate_limiter(cls):
        rate_limiter = None
        if settings.ENABLE_RATE_LIMITER:
            rate_limiter = InMemoryRateLimiter(
                requests_per_second=0.3,  # <-- We can only make a request once every 2 seconds!
                check_every_n_seconds=0.1,  # Wake up every 100 ms to check whether allowed to make a request,
                max_bucket_size=10,  # Controls the maximum burst size.
            )
        return rate_limiter

    def invoke(self, *args, **kwargs):
        """
        The final invoke method that takes any arguments that is to be finally added in the prompt message and invokes the llm call.
        """

        sucessfull_parsing = False

        prompt_value = self.llm_prompt.format_prompt(
            format_instructions=self.format_instructions, **kwargs
        )
        messages = prompt_value.to_messages()
        _message = messages
        response = ""

        try:
            response = self.model.invoke(
                _message,
                config={
                    "metadata": kwargs.get("metadata", {}),
                },
            ).content

            _message = messages
        except Exception as ex:
            # ()
            log.warning(f"[!] Error while llm invoke: {ex}")
            try:
                _message = messages[0].content
            except Exception:
                return "", sucessfull_parsing, messages

        messages = messages[0].content if isinstance(messages, list) else messages

        try:
            if self.output_parser is not None:
                # try to parse the content as dict
                raw_response = response
                response = self.output_parser.parse_with_prompt(response, prompt_value)
                sucessfull_parsing = True
                return response, sucessfull_parsing, raw_response
        except Exception as ex:
            # else return the content as it is
            log.warning(f"[!] Error while llm response parsing: {ex}")

        return response, sucessfull_parsing, messages

    @classmethod
    def get_llm(cls, model_name: str, llm_config: dict = {}):
        if settings.CUSTOM_LLM_INSTANCE:
            return settings.CUSTOM_LLM_INSTANCE
        return init_chat_model(
            model_name, max_retries=cls.MAX_RETRIES, rate_limiter=cls._get_rate_limiter(), **llm_config
        )

    @classmethod
    def build(
        cls,
        model_name: str = "azure",
        llm_config: dict = {},
        prompt_template=ChatPromptTemplate,
        output_parser=StructuredOutputParser,
        response_schemas: list[ResponseSchema] = None,
        template_string: str = "",
        *args,
        **kwargs,
    ):
        """
        Args:
            model_name: type of model either azure, openai
            api_config: holds the api key, api url, version and deployment name
            prompt_template: one of langchain.prompts Prompt Template
            template_string: The prompt template string.
            response_schemas: response schema for the output.

        Returns:
            ChatModelLLM (obj): instance of builded ChatModelLLM
        """

        return cls(
            model_name=model_name,
            config={**llm_config},
            prompt_template=prompt_template,
            output_parser=output_parser,
            template_string=template_string,
            response_schemas=response_schemas,
            *args,
            **kwargs,
        )
