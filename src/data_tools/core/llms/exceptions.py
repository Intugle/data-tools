class LLMError(Exception):
    """Base class for all LLM-related errors."""

    def __init__(self, message: str, *, provider: str | None = None):
        super().__init__(message)
        self.provider = provider

    def __str__(self) -> str:
        return self.args[0] if self.args else "An unknown LLM error occurred."


class ProviderNotFoundError(LLMError):
    """Raised when the requested LLM provider is not supported."""

    def __init__(self, provider: str, available_providers: list[str]):
        self.available_providers = available_providers
        message = (
            f"Unsupported LLM provider: '{provider}'.\n"
            f"Available providers: {', '.join(available_providers)}"
        )
        super().__init__(message, provider=provider)

    def __str__(self) -> str:
        return (
            f"Unsupported LLM provider: '{self.provider}'.\n"
            f"Available providers: {', '.join(self.available_providers)}"
        )


class MissingApiKeyError(LLMError):
    """Raised when the API key for the provider is missing."""

    def __init__(self, provider: str, env_var: str):
        self.env_var = env_var
        message = (
            f"Missing API key for provider '{provider}'.\n"
            f"Please set the environment variable '{env_var}'."
        )
        super().__init__(message, provider=provider)

    def __str__(self) -> str:
        return (
            f"Missing API key for provider '{self.provider}'.\n"
            f"Please set the environment variable '{self.env_var}'."
        )
