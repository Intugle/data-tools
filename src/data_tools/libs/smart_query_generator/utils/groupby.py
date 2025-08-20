from copy import deepcopy

from ..models.models import (
    CategoryType,
    ETLModel,
    FieldDetailsModel,
    FieldType,
    RangeOptions,
)

INITIAL_FILTERS = {"fields": [], "condition": "AND"}


class GroupBy:
    def __init__(
        self,
        etl: ETLModel,
        field_details: dict[int, FieldDetailsModel],
        data_categories: dict[str, list],
    ):
        self.__keys = []
        self.__having = deepcopy(INITIAL_FILTERS)
        self.__etl = etl
        self.__field_details = field_details
        self.__data_categories = data_categories

    def build_keys(self):
        is_mixed_category = False
        _keys = []
        if (
            len(self.__data_categories["dimension"]) > 0
            and len(self.__data_categories["measure"]) > 0
        ):
            is_mixed_category = True

        if is_mixed_category:
            for _field in self.__etl.fields:
                if (
                    _field.id in self.__data_categories["dimension"]
                    and _field.category == CategoryType.dimension
                ):
                    field_detail = self.__field_details[_field.id]
                    renameCol = (
                        _field.name
                        if field_detail.type == FieldType.calculated_field or _field.dimension_func is not None
                        else None
                    )
                    _keys.append(
                        {
                            "dataset": field_detail.asset_name,
                            "field": field_detail.name,
                            "sql_code": field_detail.sql_code,
                            "renameCol": renameCol,
                        }
                    )
            self.__keys = _keys

    def __get_field_name(self, id):
        for _field in self.__etl.fields:
            if _field.id == id:
                return _field.name

    def build_having(self):
        fields = []
        measure_filter = self.__etl.measure_filter
        if measure_filter is None:
            return
        for range in measure_filter.range:
            if range.option == RangeOptions.none:
                continue
            # field_name = self.__get_field_name(range.id)
            field_name = range.alias
            if field_name is None:
                continue
            if range.option != RangeOptions.at_most:
                fields.append(
                    {
                        "sql_code": field_name,
                        "operator": "greater_than_equal_to",
                        "params": {"value": range.value[0]},
                    }
                )
            if range.option != RangeOptions.at_least:
                fields.append(
                    {
                        "sql_code": field_name,
                        "operator": "less_than_equal_to",
                        "params": {"value": range.value[1]},
                    }
                )

        self.__having["fields"].extend(fields)

    def build(self):
        self.build_keys()
        self.build_having()

    def get_group_by(self):
        return {"keys": self.__keys, "having": self.__having}
