from intugle.analysis.models import DataSet as DataSet
from intugle.data_product import DataProduct as DataProduct
from intugle.semantic_model import SemanticModel as SemanticModel

# Expose NoSQL components if dependencies are available
try:
    from intugle.nosql.api import NoSQLToRelationalParser
    from intugle.nosql.source import MongoSource
    from intugle.nosql.writer import ParquetTarget
except ImportError:
    # Dependencies (pandas/pyarrow/pymongo) might not be installed
    pass
