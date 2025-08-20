"""
JOIN type:
{
    "0": {
        "dataset_id":
        "join_type": "inner" | "right" | "left" | "full"
        "fields": list[LinkModel]
    }
}
"""

import re

from typing import Callable

from pydantic import TypeAdapter

# from libs.smart_query_generator.src.SmartQueryGenerator import SmartQueryGenerator
from ..models.models import (
    CategoryType,
    ETLModel,
    FieldDetailsModel,
    FieldsModel,
    FieldType,
    LinkModel,
    MeasureFunctionType,
)

SEPERATOR = "____"
SQL_CODE_REGEX_PATTERN = r"@\{([\d\-]+)\}\[([\w\-\.\`]+)\]"
CF_REGEX_PATTERN = r"([A-Za-z_\s]+)\(([^()]+)\)"


class CTE:
    def __init__(
        self,
        join: dict,
        etl: ETLModel,
        field_details: dict[int, FieldDetailsModel],
        SmartQueryGenerator,
        field_details_fetcher: Callable[
            [list[int]], dict[int, list[FieldDetailsModel]]
        ],
        links: list[LinkModel],
        can_view_pii: bool = True,
        uniqueness_threshold: int = 1,
        sql_code_regex_pattern=SQL_CODE_REGEX_PATTERN,
    ):
        self.__join = join
        self.__etl = etl
        self.__ctes = []
        self.__field_details = field_details
        self.__can_view_pii = can_view_pii
        self.__uniqueness_threshold = uniqueness_threshold
        self.__sql_code_regex_pattern = sql_code_regex_pattern

        # FIXME don't pass like this think better design to prevent circular import
        self.__SmartQueryGenerator = SmartQueryGenerator

        self.__field_details_fetcher = field_details_fetcher
        self.__links = links

    # TODO need proper logic for composite key
    def __check_if_need_to_create_cte(self, link: list[LinkModel]):
        flag = True
        ta = TypeAdapter(list[LinkModel])
        link = ta.validate_python(link)
        for _l in link:
            source = self.__field_details[_l.source_field_id]
            target = self.__field_details[_l.target_field_id]
            source_uniqueness = source.distinct_count / source.count
            target_uniqueness = target.distinct_count / target.count

            if (
                source_uniqueness >= self.__uniqueness_threshold
                or target_uniqueness >= self.__uniqueness_threshold
            ):
                flag = False
                break

        return flag
    
    def get_cte_assets(self):
        join = self.__join
        assets: dict[int, list[int]] = {}

        for _join in join.values():
            fields = _join.get("fields")
            if fields is None or len(fields) <= 0:
                continue

            ta = TypeAdapter(list[LinkModel])
            links = ta.validate_python(fields)

            if not self.__check_if_need_to_create_cte(links):
                continue

            # for _join in join.values()
            for link in links:
                if link.ignore:
                    continue
                if link.source_asset_id not in assets:
                    assets[link.source_asset_id] = []
                if link.target_asset_id not in assets:
                    assets[link.target_asset_id] = []

                assets[link.source_asset_id].append(link.source_field_id)
                assets[link.target_asset_id].append(link.target_field_id)

        return assets

    def __generate_cte(self):
        join = self.__join

        if len(join.keys()) <= 1:
            return

        assets = self.get_cte_assets()

        # For fields: if mutilple fields (composite) are used for joining assets
        for _join in join.values():
            fields = _join.get("fields")
            if fields is None or len(fields) <= 0:
                continue

            ta = TypeAdapter(list[LinkModel])
            links = ta.validate_python(fields)

            for link in links:
                if link.ignore:
                    continue
                if link.source_asset_id in assets:
                    assets[link.source_asset_id].append(link.source_field_id)
                if link.target_asset_id in assets:
                    assets[link.target_asset_id].append(link.target_field_id)

        for _asset, _fields in assets.items():
            self.__generate_cte_asset(_asset, _fields)

    def __generate_cte_asset(self, asset_id: int, join_fields: list[int]):
        __field_details_update: dict[int, FieldDetailsModel] = {}
        __new_calc_field_details: dict[int, FieldDetailsModel] = {}
        _field_ids = {}

        _fields = []

        join_fields = list(set(join_fields))

        name = ""

        """
        1. Get sql code complete string of same asset group by
        2. if asset not equals to asset passed then continue
        3. insert into _fields with proper name
        """

        def _proccess_calculated_field(field: FieldsModel):
            _field_detail = self.__field_details[field.id]
            sql_code, fields = self.get_function_fields(
                _field_detail.id, _field_detail.sql_code, __new_calc_field_details
            )

            for index, (_id, _field) in enumerate(fields.items()):
                if _field["asset_id"] == asset_id:
                    _new_calc_field_id = -(int(f"{field.id}{index}"))

                    _new_calc_field_name = (
                        f"{field.name}{SEPERATOR}{-_new_calc_field_id}"
                    )

                    _new_calc_field = field.model_copy()
                    _new_calc_field.id = _new_calc_field_id
                    _new_calc_field.name = _new_calc_field_name
                    _new_calc_field.measure_func = MeasureFunctionType.aggregate

                    _fields.append(_new_calc_field)

                    _new_calc_field_details = _field_detail.model_copy()
                    _new_calc_field_details.id = _new_calc_field_id
                    _new_calc_field_details.name = _new_calc_field_name
                    _new_calc_field_details.sql_code = _field["sql_code"]
                    _new_calc_field_details.asset_id = asset_id

                    __new_calc_field_details[_new_calc_field_id] = (
                        _new_calc_field_details
                    )

                    __field_details_update[_new_calc_field_id] = (
                        _new_calc_field_details.model_copy()
                    )
                    __field_details_update[
                        _new_calc_field_id
                    ].sql_code = _new_calc_field_name

                    # udpate sql_code
                    sql_code = sql_code.replace(
                        _id, f"@{{{_new_calc_field_id}}}[{_new_calc_field_name}]"
                    )
                    self.__field_details[field.id].sql_code = sql_code

        for field in self.__etl.fields:
            field_detail = self.__field_details[field.id]
            if field_detail.type == FieldType.source:
                if field_detail.asset_id == asset_id:
                    name = field_detail.asset_name
                    _field_ids[field_detail.id] = field.category
                    cte_field = field.model_copy()
                    cte_field.dimension_func = None
                    if cte_field.measure_func == MeasureFunctionType.countDistinct and cte_field.category == CategoryType.measure:
                        cte_field.category = CategoryType.dimension
                    _fields.append(cte_field)

                    __field_details_update[field.id] = field_detail.model_copy()
                    __field_details_update[
                        field.id
                    ].sql_code = f"`{field_detail.asset_name}`.`{field.name}`"
                    # __field_details_update[field.id].sql_code = field.name

            elif field_detail.type == FieldType.calculated_field:
                _proccess_calculated_field(field)

        for field_id in join_fields:
            if field_id not in _field_ids.keys():
                _field_detail = self.__field_details[field_id]
                name = _field_detail.asset_name
                if _field_detail.type == FieldType.source:
                    # FIXME slim possibility for names getting collision
                    field_name = _field_detail.name
                    # field_name = (
                    #     _field_detail.name + SEPERATOR + _field_detail.asset_name
                    # )
                    _field = FieldsModel(
                        id=_field_detail.id,
                        name=field_name,
                        type=_field_detail.type,
                        category=CategoryType.dimension,
                    )
                    _field_ids[_field_detail.id] = CategoryType.dimension
                    _fields.append(_field)

                    __field_details_update[field_id] = _field_detail.model_copy()
                    # __field_details_update[field_id].sql_code = field_name
                    __field_details_update[
                        field_id
                    ].sql_code = f"`{_field_detail.asset_name}`.`{field_name}`"
                elif _field_detail.type == FieldType.calculated_field:
                    _field = FieldsModel(
                        id=field_id,
                        name=_field_detail.name,
                    )
                    _proccess_calculated_field(_field)
            else:
                # SWAP join field id and etl field id
                if _field_ids[field_id] == CategoryType.measure:
                    # Create new field
                    _field_detail = self.__field_details[field_id]
                    # FIXME name may collide with user name
                    _field_name = f"join_{_field_detail.name}"

                    new_field_id = f"join_{field_id}"
                    self.__field_details[new_field_id] = _field_detail
                    _field = FieldsModel(
                        id=field_id,
                        name=_field_name,
                        type=_field_detail.type,
                        category=CategoryType.dimension,
                        # dimension_func=DimensionFunctionType.distinct,
                    )
                    _field_ids[_field_detail.id] = CategoryType.dimension

                    for field in _fields:
                        if field.id == field_id:
                            field.id = new_field_id

                    _fields.append(_field)

                    __field_details_update[new_field_id] = __field_details_update[
                        field_id
                    ].model_copy()
                    __field_details_update[field_id] = _field_detail.model_copy()
                    # __field_details_update[field_id].sql_code = field_name
                    __field_details_update[
                        field_id
                    ].sql_code = f"`{_field_detail.asset_name}`.`{_field_name}`"

                    # Update etl
                    for field in self.__etl.fields:
                        if field.id == field_id:
                            field.id = new_field_id

        self.__field_details = {**self.__field_details, **__new_calc_field_details}

        etl = ETLModel(name=name, fields=_fields)

        sql_builder = self.__SmartQueryGenerator(
            etl,
            self.__field_details_fetcher,
            self.__links,
            self.__field_details,
            self.__can_view_pii,
            self.__uniqueness_threshold,
            self.__sql_code_regex_pattern,
        )
        sql_builder.build()

        query = sql_builder.get_query()

        # FIXME temp fix update measure function [count, count distinct] and dimension function
        for field in self.__etl.fields:
            _field_detail = self.__field_details[field.id]
            if _field_detail.asset_id == asset_id:
                self.__update_function_etl(field.id)

        self.__field_details = {
            **self.__field_details,
            **sql_builder.get_field_details(),
            **__field_details_update,
        }

        self.__ctes.append((name, query))

    def __update_field_ids(self, field_id: int, old_id: int, new_id: int):
        field = self.__field_details[field_id]
        sql_code = field.sql_code

        matches = re.findall(self.__sql_code_regex_pattern, sql_code)

        for match in matches:
            # _field_id = int(match[0])
            # FIXME make it better @()[]
            old_sql_code = f"@{{{old_id}}}[{match[1]}]"
            replacement_sql_code = f"@{{{new_id}}}[{match[1]}]"
            sql_code = sql_code.replace(old_sql_code, replacement_sql_code)
            # sql_code = re.sub(
            #     old_sql_code,
            #     lambda m: replacement_sql_code,
            #     sql_code
            # )

        self.__field_details[field_id].sql_code = sql_code

    def __get_base_field_ids_of_field(self, field_id: int):
        field = self.__field_details[field_id]

        field_ids = set()

        matches = re.findall(self.__sql_code_regex_pattern, field.sql_code)

        if len(matches) <= 0:
            return set([field_id])

        for match in matches:
            _field_id = int(match[0])
            field_ids = field_ids.union(self.__get_base_field_ids_of_field(_field_id))

        return field_ids

    def __get_field_ids_asset_ids(self, sql_code: str, fields: dict = {}):
        field_ids = set()
        asset_ids = set()

        matches = re.findall(self.__sql_code_regex_pattern, sql_code)

        if len(matches) <= 0:
            return field_ids, asset_ids

        for match in matches:
            _field_id = match[0]
            try:
                _field_id = int(_field_id)
            except Exception:
                ...
            field_ids.add(_field_id)

            field = fields.get(_field_id)
            if field is None:
                field = self.__field_details[_field_id]
                asset_ids.add(field.asset_id)
            else:
                asset_ids.add(field["asset_id"])

        return field_ids, asset_ids

    def __get_base_sql_code(self, sql_code: str, fields: dict = {}):
        matches = re.findall(self.__sql_code_regex_pattern, sql_code)

        if len(matches) <= 0:
            return sql_code

        for match in matches:
            _field_id = match[0]

            field = fields.get(_field_id)
            if field is None:
                continue
            temp_code = f"@{{{match[0]}}}[{match[1]}]"
            sql_code = sql_code.replace(temp_code, field["sql_code"])

        return sql_code

    def parse_function_fields(self, field_id: int, sql_code: str, fields={}):
        multiple_asset_field = False

        matches = re.findall(CF_REGEX_PATTERN, sql_code)

        for match in matches:
            func = match[0]
            args = match[1]
            _fields, _assets = self.__get_field_ids_asset_ids(args, fields)
            if len(_assets) == 1:
                _id = [field_id, *_fields, *_assets]
                new_one = "-".join([str(i) for i in _id])
                old_code = f"{func}({args})"
                new_code = f"@{{{new_one}}}[calculated_field]"
                sql_code = sql_code.replace(old_code, new_code)

                fields[new_one] = {
                    "sql_code": self.__get_base_sql_code(old_code, fields),
                    "asset_id": _assets.pop(),
                }

                multiple_asset_field = True

        if multiple_asset_field:
            sql_code, fields = self.parse_function_fields(field_id, sql_code, fields)

        return sql_code, fields

    def get_function_fields(
        self,
        field_id: int,
        sql_code: str,
        new_calc_field_details: dict[int, FieldDetailsModel],
        fields={},
    ):
        sql_code, fields = self.parse_function_fields(field_id, sql_code, fields)
        clean_fields = {}

        matches = re.findall(self.__sql_code_regex_pattern, sql_code)

        if len(matches) <= 0:
            return sql_code, clean_fields

        for match in matches:
            _id = match[0]
            field = f"@{{{match[0]}}}[{match[1]}]"
            _f = fields.get(_id)

            if _f is not None:
                clean_fields[field] = _f
                continue

            _id = int(_id)
            details = new_calc_field_details.get(_id)
            if details is not None:
                clean_fields[field] = {
                    "sql_code": details.sql_code,
                    "asset_id": details.asset_id,
                }
                continue

            clean_fields[field] = {
                "sql_code": field,
                "asset_id": self.__field_details[_id].asset_id,
            }

        return sql_code, clean_fields

    # FIXME temp fix update measure function [count, count distinct] and dimension function
    def __update_function_etl(self, field_id: int):
        fields = self.__etl.fields
        for field in fields:
            if field.id == field_id and field.measure_func in [
                MeasureFunctionType.count,
                # MeasureFunctionType.countDistinct,
            ]:
                field.measure_func = MeasureFunctionType.sum
            # if field.id == field_id and field.measure_func == MeasureFunctionType.countDistinct:
            #     field.measure_func = MeasureFunctionType.sum

    def build(self):
        self.__generate_cte()

    def get_ctes(self):
        return self.__ctes

    def get_etl(self):
        return self.__etl

    def get_links(self):
        return self.__links

    def get_field_details(self):
        return self.__field_details
