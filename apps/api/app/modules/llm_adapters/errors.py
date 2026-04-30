class LlmAdapterError(RuntimeError):
    pass


class LlmProviderNotConfiguredError(LlmAdapterError):
    pass


class UnknownLlmProviderError(LlmAdapterError):
    pass
