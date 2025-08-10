import logging
import time

from typing import TYPE_CHECKING

import openai

from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import BaseChatPromptTemplate, ChatPromptTemplate
from langchain_community.callbacks.openai_info import OpenAICallbackHandler
from langchain_openai.chat_models import AzureChatOpenAI, ChatOpenAI

from .config import get_llm_config

log = logging.getLogger(__name__)


if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel


class ChatModelLLM:
    '''
    A Wrapper around Chat LLM to invoke on any of the pipeline that uses llm
    '''

    call_backs = [OpenAICallbackHandler()]

    # type of chat models to support
    CHAT_MODELS = {
        "azure": AzureChatOpenAI,
        "openai": ChatOpenAI
    }

    model = None
    # number of retries to the LLM.
    MAX_RETRIES = 5

    # time to sleep if we hit llm RateLimitError
    SLEEP_TIME = 25

    def __init__(self, model_name: str, response_schemas: list[ResponseSchema] = None,
                 output_parser=StructuredOutputParser, prompt_template=ChatPromptTemplate, template_string: str = None, config: dict = {},
                 *args, **kwargs
                 ):
        
        self.model: BaseChatModel = self.CHAT_MODELS[model_name](**config)  # the llm model
      
        self.parser: StructuredOutputParser = output_parser  # the output parser
        
        self.prompt_template: BaseChatPromptTemplate = prompt_template  # prompt template 

        self.output_parser = self.__output_parser_builder__(response_schemas=response_schemas) if response_schemas is not None else None  # the builded output parser

        self.format_instructions = self.output_parser.get_format_instructions() if self.output_parser is not None else None  # the format instructions

        self.llm_prompt = self.prompt_template.from_template(template=template_string)  # get the final builded prompt template

    def chat(self, msg):
        
        return self.model.invoke(msg).content
    
    def __output_parser_builder__(self, response_schemas: list[ResponseSchema] = None):
        """
            for building the corresponding output paraser from the given ResponseSchema
        """
        output_parser = self.parser.from_response_schemas(response_schemas=response_schemas)
        return output_parser
    
    def message_builder():
        ...

    def invoke(self, *args, **kwargs):
        """
            The final invoke method that takes any arguments that is to be finally added in the prompt message and invokes the llm call.
        """

        # format_instructions = ""
        # output_parser = None
        # if response_schemas:
        #     output_parser = self.parser.from_response_schemas(response_schemas=response_schemas)
        #     format_instructions = output_parser.get_format_instructions()
        
        # prompt = self.prompt_template.from_template(template = template_string)
        
        sucessfull_parsing = False

        messages = self.llm_prompt.format(
                format_instructions=self.format_instructions,
                **kwargs
        )
        # ()
        retries = 0
        _message = messages
        response = ""

        while True:
            try:
                if retries > self.MAX_RETRIES: 
                    break
                
                response = self.model.invoke(_message,
                  config={'callbacks': self.call_backs,
                          "metadata": kwargs.get("metadata", {}),
                }).content

                _message = messages
                break
            except openai.RateLimitError:
                log.warning(f"[!] LLM API rate limit hit ... sleeping for {self.SLEEP_TIME} seconds")
                time.sleep(self.SLEEP_TIME)
            except Exception as ex:
                # ()
                log.warning(f"[!] Error while llm invoke: {ex}")
                try:
                    _message = messages[0].content
                except Exception:
                    return "", sucessfull_parsing, messages
                # response = self.model.invoke(messages[0].content).content
            retries += 1
        
        messages = messages[0].content if isinstance(messages, list) else messages   

        try:
            if self.output_parser is not None:
                # try to parse the content as dict
                raw_response = response
                response = self.output_parser.parse(response)
                sucessfull_parsing = True
                return response, sucessfull_parsing, raw_response
        except Exception as ex:
            # else return the content as it is
            log.warning(f"[!] Error while llm response parsing: {ex}")
        
        return response, sucessfull_parsing, messages

    @classmethod
    def get_llm(cls, model_name: str = "azure", api_config: dict = {}, other_config: dict = {}):

        config = {**get_llm_config(api_config, type=model_name), **other_config}

        return cls.CHAT_MODELS[model_name](**config)

    @classmethod
    def build(cls,
              model_name: str = "azure",
              api_config: dict = {},
              other_config: dict = {},
              prompt_template=ChatPromptTemplate,
              output_parser=StructuredOutputParser,
              response_schemas: list[ResponseSchema] = None,
              template_string: str = "",
              *args, **kwargs
              ):
        '''
            Args:
                model_name: type of model either azure, openai
                api_config: holds the api key, api url, version and deployment name
                prompt_template: one of langchain.prompts Prompt Template
                template_string: The prompt template string.
                response_schemas: response schema for the output.
            
            Returns:
                ChatModelLLM (obj): instance of builded ChatModelLLM
        '''
        
        return cls(
            model_name=model_name,
            config={**get_llm_config(api_config, type=model_name), **other_config},
            prompt_template=prompt_template,
            output_parser=output_parser,
            template_string=template_string,
            response_schemas=response_schemas,
            *args, **kwargs
        )
        
        
