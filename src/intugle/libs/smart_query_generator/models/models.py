from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator

from intugle.libs.smart_query_generator.utils.helpers import normalize_column_name


class MeasureFunctionType(str, Enum):
    count = "count"
    countDistinct = "countDistinct"
    sum = "sum"
    average = "average"
    aggregate = "aggregate"
    max = "max"


class DimensionFunctionType(str, Enum):
    year = "year"
    month = "month"
    day = "day"
    yearMonth = "yearMonth"
    distinct = "distinct"


class WildCardOptions(str, Enum):
    contains = "contains"
    starts_with = "starts_with"
    ends_with = "ends_with"
    exactly_matches = "exactly_matches"
    formula = "formula"
    equals = "equals"
    not_equals = "not_equals"
    greater_than = "greater_than"
    less_than = "less_than"
    greater_than_equal_to = "greater_than_equal_to"
    less_than_equal_to = "less_than_equal_to"


class RangeOptions(str, Enum):
    none = None
    range = "range"
    at_least = "at_least"
    at_most = "at_most"


class FieldType(str, Enum):
    source = "source"
    calculated_field = "calculated_field"


class CategoryType(str, Enum):
    dimension = "dimension"
    measure = "measure"


class SortDirection(str, Enum):
    asc = "asc"
    desc = "desc"


class JoinOpt(str, Enum):
    all = "all"
    common = "common"


class SelectionModel(BaseModel):
    id: int | str
    exclude: Optional[bool] = None
    null: Optional[bool] = None
    values: Optional[list[str | int | float]] = None
    dimFunc: Optional[DimensionFunctionType] = None


class WildCardModel(BaseModel):
    id: int | str
    value: str
    exclude: Optional[bool] = None
    option: WildCardOptions = WildCardOptions.contains
    dimFunc: Optional[DimensionFunctionType] = None


class ConditionModel(BaseModel): ...


class SortByModel(BaseModel):
    id: int | str
    alias: Optional[str] = None
    direction: SortDirection = SortDirection.asc


class FilterModel(BaseModel):
    selections: Optional[list[SelectionModel]] = []
    wildcards: Optional[list[WildCardModel]] = []
    conditions: Optional[list[ConditionModel]] = []
    limit: Optional[int] = None
    offset: Optional[int] = None
    sort_by: Optional[list[SortByModel]] = []


class FieldsModel(BaseModel):
    id: Optional[int | str] = None
    name: str
    type: FieldType = FieldType.source
    category: CategoryType = CategoryType.dimension
    measure_func: MeasureFunctionType = MeasureFunctionType.count
    dimension_func: Optional[DimensionFunctionType] = None
    is_pii: bool = False
    sql_code: Optional[str] = None
    join_opt: Optional[JoinOpt] = None

    @field_validator("name", mode="before")
    def normalize_name(cls, v):
        if isinstance(v, str):
            return normalize_column_name(v)
        return v


class RangeModel(BaseModel):
    id: int | str
    alias: str
    value: tuple[int, int]
    option: RangeOptions


class MeasureFilterModel(BaseModel):
    range: list[RangeModel] = []


class ETLModel(BaseModel):
    name: str
    fields: list[FieldsModel]
    filter: Optional[FilterModel] = None
    measure_filter: Optional[MeasureFilterModel] = None
    cart_id: int = 0
    join: Optional[dict] = None

    def __str__(self):
        return self.model_dump_json()


class FieldDetailsModel(BaseModel):
    id: int | str
    name: str
    type: FieldType = FieldType.source
    datatype_l1: str
    datatype_l2: str
    sql_code: str
    is_pii: bool
    asset_id: int | str
    asset_name: str
    asset_details: dict
    connection_id: int | str
    connection_source_name: str
    connection_credentials: dict
    count: Optional[int] = 1
    distinct_count: Optional[int] = 1


class SinkModel(BaseModel):
    connection_id: int
    connection_source_name: str
    connection_credentials: dict
    destination: str


class LinkType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class LinkModel(BaseModel):
    id: int | str
    source_field_ids: list[int | str]
    target_field_ids: list[int | str]
    source_asset_id: int | str
    target_asset_id: int | str
    type: LinkType
    source_count: int = 1
    target_count: int = 1
    source_count_distinct: int = 1
    target_count_distinct: int = 1
    records_mapped: int = 1
    score: Optional[int] = None
    ignore: Optional[bool] = False

    @field_validator("records_mapped", mode="before")
    def default_if_none(cls, v):
        return v if v is not None else 1
