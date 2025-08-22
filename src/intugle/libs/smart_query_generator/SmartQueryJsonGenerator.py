"""
    class ETLModel(BaseModel):
        name: str
        fields: list[FieldsModel]
        filter: Optional[FilterModel] = None
        destination: str  # need or remove it?

STEPS:
1. Get all information about fields needed with configuration and all
    > Check if all fields selected are valid and user have access by checking the length of fields selected and fetched data
2. Generate source and dataset
    > What if the table is virtual not source
    > Need recursion ??
    > Builder pattern ??
3. Generate query
    a. Create CTE when needed:
        a. Check if is a virtual table, if yes create cte
        b. Check count and count distinct of the table if distinct then create cte (Recursive)
    b. Merge CTE to create complete sql
    c. User able to change joins
"""

from typing import Callable

from .models.models import ETLModel, FieldDetailsModel, LinkModel, SinkModel
from .SmartQueryGenerator import SmartQueryGenerator
from .utils.get_fields_ids_from_elt_model import get_fields_ids_from_etl_model


class NodeType:
    SOURCE = "SOURCE"
    MODEL = "MODEL"


class SmartQueryJsonGenerator:
    def __init__(
        self,
        etl: ETLModel,
        field_details_fetcher: Callable[[list[int]], dict[int, FieldDetailsModel]],
    ):
        self.__etl = ETLModel.model_validate(etl)
        self.cart_id = self.__etl.cart_id
        self.name = self.__etl.name
        self.__field_details_fetcher = self.__get_field_details_fetcher(
            field_details_fetcher
        )

        self.source = []
        self.dataset = []
        self.sink = []
        self.post_transform = {}
        self.transform = {}
        self.sql_query = ""
        self.__join = {}
        self.__field_details: dict[int, FieldDetailsModel] = {}

        self.__fetch_fields_details()

    def __get_field_details_fetcher(
        self, field_details_fetcher: Callable[[list[int]], dict[int, FieldDetailsModel]]
    ):
        def _field_details_fetcher(fields: list[int, str]):
            _fields = [x for x in fields if isinstance(x, int)]
            return field_details_fetcher(_fields)

        return _field_details_fetcher

    def __fetch_fields_details(self):
        _fields = get_fields_ids_from_etl_model(self.__etl)

        __field_details = self.__field_details_fetcher(_fields)

        self.__field_details = {**self.__field_details, **__field_details}

    @staticmethod
    def __get_source(field_detail: FieldDetailsModel | SinkModel):
        source_name = field_detail.connection_source_name
        creds = field_detail.connection_credentials
        connection_id = field_detail.connection_id

        source = {
            "id": str(connection_id),
            "connection_details": creds,
            "type": source_name,
        }
        return source

    @staticmethod
    def __get_dataset(field_detail: FieldDetailsModel):
        dataset = {
            "id": str(field_detail.asset_id),
            "source_id": str(field_detail.connection_id),
            "name": field_detail.asset_name,
            "details": field_detail.asset_details,
            "metadata": {
                # Extend later
                "count": field_detail.count
            },
        }
        return dataset

    @staticmethod
    def __get_sink(
        connection_id: int,
        asset_id: int,
        asset_name: str,
        details: dict,
    ):
        return {
            "id": str(connection_id),
            "source_id": str(asset_id),
            "name": asset_name,
            "details": details,
        }

    def __add_source_dataset(self, field_detail: FieldDetailsModel):
        self.source.append(self.__get_source(field_detail))
        self.dataset.append(self.__get_dataset(field_detail))

    def build_source_dataset(self):
        for field in self.__field_details.values():
            self.__add_source_dataset(field)

    def build_sink(self, sink_details: SinkModel):
        sink_details = SinkModel.model_validate(sink_details)

        src = self.__get_source(sink_details)

        self.source.append(src)

        # FIXME Pass details to the function ?
        details = {
            "name": f"{sink_details.destination}/{self.cart_id}",
            "format": "parquet",
        }
        self.sink = [
            self.__get_sink(
                connection_id=sink_details.connection_id,
                asset_id=self.cart_id,
                asset_name=f"cart_{self.cart_id}",
                details=details,
            )
        ]

    def build_sql(self, links: list[LinkModel], cte: bool = True):
        sql_builder = SmartQueryGenerator(
            self.__etl, self.__field_details_fetcher, links, self.__field_details
        )

        sql_builder.build(cte)
        sql_query = sql_builder.get_query()

        self.__join = sql_builder.get_join()
        self.__field_details = {
            **self.__field_details,
            **sql_builder.get_field_details(),
        }

        self.sql_query = sql_query

        return self.sql_query

    def build(self, sink_details: SinkModel, links: list[LinkModel]):
        self.build_sql(links)
        self.build_source_dataset()
        self.build_sink(sink_details)

    def get_json(self):
        return {
            "name": self.name,
            "sources": self.source,
            "datasets": self.dataset,
            "sql_query": self.sql_query,
            "sink": self.sink,
            "cart_id": self.cart_id,
        }

    def get_field_details(self):
        _field_details = {
            key: val
            for key, val in self.__field_details.items()
            if isinstance(key, int)
        }
        return _field_details

    def get_join(self):
        return self.__join

    def get_sql_query(self):
        return self.sql_query
