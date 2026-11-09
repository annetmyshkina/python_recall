class AiProviderError(RuntimeError):
    """Base error for expected and safely handled provider failures."""


class AiProviderUnavailableError(AiProviderError):
    """The provider cannot currently be reached or returned an HTTP error."""


class AiProviderTimeoutError(AiProviderError):
    """The provider did not answer within the configured deadline."""


class AiProviderResponseError(AiProviderError):
    """The provider response did not match the expected contract."""


class AiDisabledError(AiProviderError):
    """An AI operation was requested while AI is disabled."""


class AiModelMissingError(AiProviderError):
    """The configured model is not installed in the provider."""
