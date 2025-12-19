from typing import Iterator, Dict, Any
import pymongo


class NoSQLSource:
    """Base interface for NoSQL data sources."""

    def get_data(self) -> Iterator[Dict[str, Any]]:
        raise NotImplementedError


class MongoSource(NoSQLSource):
    """Reads data from a MongoDB collection."""

    def __init__(self, uri: str, database: str, collection: str, sample_size: int = 0):
        self.uri = uri
        self.database = database
        self.collection = collection
        self.sample_size = sample_size
        self._client = None

    def _connect(self):
        if not self._client:
            self._client = pymongo.MongoClient(self.uri)

    def get_data(self) -> Iterator[Dict[str, Any]]:
        self._connect()
        db = self._client[self.database]
        coll = db[self.collection]

        cursor = coll.find()
        if self.sample_size > 0:
            cursor = cursor.limit(self.sample_size)

        for doc in cursor:
            # Convert ObjectId to string to avoid serialization issues later
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            yield doc
