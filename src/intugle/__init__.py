from intugle.analysis.models import DataSet as DataSet
from intugle.data_product import DataProduct as DataProduct
from intugle.semantic_model import SemanticModel as SemanticModel

__all__ = ["DataSet", "DataProduct", "SemanticModel"]

# Expose NoSQL components if dependencies are available
try:
    from intugle.nosql.api import NoSQLToRelationalParser  # noqa: F401
    from intugle.nosql.source import MongoSource  # noqa: F401
    from intugle.nosql.writer import ParquetTarget  # noqa: F401

    __all__.extend(["NoSQLToRelationalParser", "MongoSource", "ParquetTarget"])
except ImportError:
    # Dependencies (pandas/pyarrow/pymongo) might not be installed
    pass
