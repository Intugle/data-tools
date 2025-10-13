import re

from typing import Optional

# ---------------------------------------------------------------------
# SECURITY HELPERS
# ---------------------------------------------------------------------

SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_identifier(name: str) -> str:
    """Validate and return a safe SQL identifier (double-quote-wrapped)."""
    if not name:
        raise ValueError("Identifier cannot be empty.")
    if not SAFE_IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return f"\"{name}\""


def escape_literal(value: Optional[str]) -> str:
    """Escape literal values used inside SQL strings."""
    if value is None:
        return "NULL"
    # For comments, we just need to remove newlines, not wrap in quotes.
    return str(value).replace("\n", " ").replace("\r", " ")
