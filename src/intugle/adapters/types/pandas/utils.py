
from typing import Any

import numpy as np


def convert_to_native(value: Any) -> Any:
    """Recursively converts numpy types to native Python types."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [convert_to_native(v) for v in value]
    return value