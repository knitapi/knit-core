"""Error types step code raises.

Classify every failure on purpose:
  TerminalFlowError  - retrying cannot help (bad credentials, bad request, missing required thing). The step fails now.
  TransientFlowError - retrying may help (429, 5xx, timeouts). Knit's runner runs the step again.

Locally (mock mode) these are plain exceptions with a `non_retryable` flag. On Knit's runner the same names are provided by
the runner, which turns them into retry or fail decisions.
"""


class FlowError(Exception):
    """Base class. Raise one of the two subclasses below, not this directly."""

    non_retryable: bool = False

    def __init__(self, message: str = "", non_retryable: bool | None = None):
        super().__init__(message)
        self.message = message
        if non_retryable is not None:
            self.non_retryable = non_retryable


class TerminalFlowError(FlowError):
    def __init__(self, message: str):
        super().__init__(message, non_retryable=True)


class TransientFlowError(FlowError):
    def __init__(self, message: str):
        super().__init__(message, non_retryable=False)