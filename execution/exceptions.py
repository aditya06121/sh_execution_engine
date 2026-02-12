class CompileError(Exception):
    """Raised when compilation fails."""
    pass


class RuntimeExecutionError(Exception):
    """Raised when user code crashes during execution."""
    pass


class ExecutionTimeoutError(Exception):
    """Raised when execution exceeds time limit."""
    pass
