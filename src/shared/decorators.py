from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from loguru import logger

P = ParamSpec("P")
R = TypeVar("R")


def log_errors(func: Callable[P, R]) -> Callable[P, R]:
    """Catch, log, and re-raise any exception raised by the decorated method.

    The log line includes the fully-qualified function name, exception type,
    and message so the source is immediately identifiable without a traceback.

    Usage::

        @log_errors
        def execute(self, query: str) -> dict: ...
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error(f"[{func.__qualname__}] {type(exc).__name__}: {exc}")
            raise

    return wrapper
