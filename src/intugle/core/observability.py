from typing import TYPE_CHECKING, List, Optional

from intugle.core.settings import settings

if TYPE_CHECKING:
    from langfuse.callback import CallbackHandler


def get_langfuse_handler(
    trace_name: str, tags: Optional[List[str]] = None
) -> Optional["CallbackHandler"]:
    """
    Initializes and returns a Langfuse CallbackHandler if enabled in settings.

    Args:
        trace_name: The name for the Langfuse trace.
        tags: A list of tags to associate with the trace.

    Returns:
        An instance of CallbackHandler if Langfuse is enabled and configured,
        otherwise None.
    """
    if not settings.LANGFUSE_ENABLED:
        return None

    try:
        from langfuse.callback import CallbackHandler
    except ImportError:
        print("Warning: Langfuse is enabled, but the 'langfuse' package is not installed.")
        print("Please install it with: pip install langfuse")
        return None

    if not all([settings.LANGFUSE_PUBLIC_KEY, settings.LANGFUSE_SECRET_KEY]):
        print("Warning: Langfuse is enabled but public or secret key is missing.")
        return None

    try:
        handler = CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            trace_name=trace_name,
            tags=tags or ["key-identification-agent"],
        )
        handler.auth_check()
        print("[*] Langfuse tracing is active.")
        return handler
    except Exception as e:
        print(f"Error initializing Langfuse: {e}")
        return None
