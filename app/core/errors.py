"""Application errors that are safe to surface without leaking credentials."""


class LLMConfigurationError(ValueError):
    """The local LLM configuration is missing or invalid."""


class LLMRequestError(RuntimeError):
    """A normalized OpenRouter/OpenAI-compatible request failure."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
