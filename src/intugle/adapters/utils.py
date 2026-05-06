
import re

from collections.abc import Sequence
from typing import Any

import numpy as np


def convert_to_native(value: Any) -> Any:
    """Recursively converts numpy types to native Python types."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [convert_to_native(v) for v in value]
    return value


def split_identifier_path(identifier: str, max_parts: int | None = None) -> list[str]:
    """Split a dotted SQL identifier path into validated parts."""
    if not isinstance(identifier, str):
        raise TypeError("SQL identifier must be a string.")

    parts = [part.strip() for part in identifier.split(".")]
    if not parts or any(not part for part in parts):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")

    if max_parts is not None and len(parts) > max_parts:
        raise ValueError(
            f"Invalid SQL identifier {identifier!r}: expected at most {max_parts} part(s)."
        )

    return parts


def quote_identifier(identifier: str, quote_char: str = '"') -> str:
    """Quote a single SQL identifier safely for the target dialect."""
    if not isinstance(identifier, str):
        raise TypeError("SQL identifier must be a string.")
    if identifier == "":
        raise ValueError("SQL identifier cannot be empty.")

    if quote_char == "[":
        return f"[{identifier.replace(']', ']]')}]"

    escaped = identifier.replace(quote_char, quote_char * 2)
    return f"{quote_char}{escaped}{quote_char}"


def quote_identifier_parts(
    parts: Sequence[str], quote_char: str = '"', compound: bool = False
) -> str:
    """Quote an already split SQL identifier path."""
    if not parts:
        raise ValueError("SQL identifier path cannot be empty.")

    normalized_parts = [part.strip() for part in parts]
    if any(not part for part in normalized_parts):
        raise ValueError("SQL identifier path contains an empty part.")

    if quote_char == "[":
        return ".".join(quote_identifier(part, quote_char) for part in normalized_parts)

    if compound:
        escaped = ".".join(part.replace(quote_char, quote_char * 2) for part in normalized_parts)
        return f"{quote_char}{escaped}{quote_char}"

    return ".".join(quote_identifier(part, quote_char) for part in normalized_parts)


def quote_identifier_path(
    identifier: str, quote_char: str = '"', max_parts: int | None = None, compound: bool = False
) -> str:
    """Quote a dotted SQL identifier path safely for the target dialect."""
    parts = split_identifier_path(identifier, max_parts=max_parts)
    return quote_identifier_parts(parts, quote_char=quote_char, compound=compound)


def escape_sql_literal(value: str) -> str:
    """Escape a string for inclusion inside a single-quoted SQL literal."""
    if not isinstance(value, str):
        raise TypeError("SQL literal value must be a string.")
    return value.replace("'", "''")


_PII_TAG_PATTERN = re.compile(r"[\s\-]+")
_PII_TAGS = {
    "pii",
    "phi",
    "sensitive",
    "sensitive_data",
    "personal_data",
    "personal_information",
    "confidential",
    "restricted",
}


def has_pii_tags(tags: Sequence[str] | None) -> bool:
    """Return whether column tags indicate PII/sensitive data."""
    if not tags:
        return False

    normalized_tags = {
        _PII_TAG_PATTERN.sub("_", tag.strip().lower())
        for tag in tags
        if isinstance(tag, str) and tag.strip()
    }

    return any(
        tag in _PII_TAGS or "pii" in tag or "phi" in tag or "sensitive" in tag
        for tag in normalized_tags
    )
