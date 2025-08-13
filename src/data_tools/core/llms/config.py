import os
from typing import Any


class ConfigError(Exception):
    """Raised when there is a configuration issue."""


class LLMConfig:
    """Centralized config loader for LLM providers."""

    @staticmethod
    def get_env_var(name: str, *, required: bool = True, default: Any = None) -> str | Any:
        value = os.getenv(name, default)
        if required and value is None:
            raise ConfigError(f"Missing required environment variable: {name}")
        return value

    @classmethod
    def load_provider_config(cls, provider: str) -> dict[str, Any]:
        """Load config for a specific provider."""
        provider = provider.lower()

        if provider == "openai":
            return {
                "api_key": cls.get_env_var("OPENAI_API_KEY"),
                "base_url": cls.get_env_var("OPENAI_API_BASE", required=False),
            }

        elif provider == "azure_openai":
            return {
                "api_key": cls.get_env_var("AZURE_OPENAI_API_KEY"),
                "endpoint": cls.get_env_var("AZURE_OPENAI_ENDPOINT"),
                "deployment_name": cls.get_env_var("AZURE_OPENAI_DEPLOYMENT"),
            }

        elif provider == "claude":
            return {
                "api_key": cls.get_env_var("CLAUDE_API_KEY"),
            }

        else:
            raise ConfigError(f"No config loader for provider '{provider}'.")


def get_llm_config(config: dict, type: str = "azure"):

    if type.__eq__("azure"):
        deployment = {
            # "model":config["API_INFO"]["DEPLOYMENT_NAME"],
            "deployment_name": config["API_INFO"]["DEPLOYMENT_NAME"],
            "openai_api_version": config["API_INFO"]["API_VERSION"],
            "azure_endpoint": config["API_INFO"]["API_BASE"],
            "openai_api_key": config["API_INFO"]["API_KEY"],
        }

    elif type.__eq__("openai"):
        deployment = config["API_INFO"]
        # deployment = {
        #     "model_name":config["API_INFO"]["DEPLOYMENT_NAME"]
        # }
    else:
        raise ValueError("[!] Invalid model type")
    return deployment