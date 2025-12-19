from intugle.analysis.models import DataSet as DataSet
from intugle.data_product import DataProduct as DataProduct
from intugle.semantic_model import SemanticModel as SemanticModel

__all__ = ["DataSet", "DataProduct", "SemanticModel"]

# Expose text processor for unstructured text-to-semantic conversion
try:
    from intugle.text_processor import TextToSemanticProcessor  # noqa: F401

    __all__.append("TextToSemanticProcessor")
except ImportError:
    # Text processor dependencies might not be available
    pass
