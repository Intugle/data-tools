import re

from typing import Callable, Optional

from pydantic import TypeAdapter

from intugle.libs.query_generator import QueryGenerator, QueryGeneratorModel

from .custom_data_types.OrderedSet import OrderedSet
from .models.models import (
    CategoryType,
    ETLModel,
    FieldDetailsModel,
    FieldsModel,
    FieldType,
    JoinOpt,
    LinkModel,
)
from .utils.cte import CTE
from .utils.filter import Filter
from .utils.groupby import GroupBy
from .utils.join import Join

# Regular expression to match the pattern @{number}[Ftext]
SQL_CODE_REGEX_PATTERN = r"@\{([\d\-]+)\}\[([\w\-\.\`]+)\]"
UNIQUENESS_THRESHOLD = 1
SEPERATOR = "____"


class SmartQueryGenerator:
    def __init__(
        self,
        etl: ETLModel,
        field_details_fetcher: Callable[[list[int]], dict[int, FieldDetailsModel]],
        links: list[LinkModel],
        field_details: dict[int, FieldDetailsModel],
        can_view_pii: bool = True,
        uniqueness_threshold: int = UNIQUENESS_THRESHOLD,
        sql_code_regex_pattern=SQL_CODE_REGEX_PATTERN,
    ):
        self.__etl = ETLModel.model_validate(etl)
        self.__field_details_fetcher = field_details_fetcher
        self.__can_view_pii = can_view_pii

        ta = TypeAdapter(list[LinkModel])
        self.__links = ta.validate_python(links)

        self.__field_details = field_details

        self.__ctes: list[tuple[Optional[str], str]] = []
        self.__assets: OrderedSet[int] = OrderedSet()
        self.__assets_join_opt = {}
        self.__join: dict[str, JoinOpt] = {}

        self.__selected_fields = []
        self.__join_json = {}
        self.__filters = {}
        self.__group_by = {}
        self.__sort_fields = []
        self.__limit = None
        self.__offset = None

        self.__data_categories = {"dimension": [], "measure": []}

        self.__sql_code_regex_pattern = sql_code_regex_pattern
        self.__uniqueness_threshold = uniqueness_threshold

    def __fetch_fields_details(self, fields: list[int]):
        __field_details = self.__field_details_fetcher(fields)

        self.__field_details = {**self.__field_details, **__field_details}

    def __get_join_names(self, join: dict):
        assets = {}
        for field in self.__field_details.values():
            if field.type == FieldType.source:
                assets[field.asset_id] = {
                    "id": field.asset_id,
                    "name": field.asset_name,
                }

        _tmp_join = join
        for _key, _value in join.items():
            _dataset = assets.get(_value["dataset_id"])
            if not _dataset:
                continue
            _tmp_join[_key]["dataset"] = _dataset["name"]
            join_conditions = []
            if "fields" not in _value:
                continue
            for link_data in _value["fields"]:
                link = LinkModel.model_validate(link_data)

                for i in range(len(link.source_field_ids)):
                    left_field_id = link.source_field_ids[i]
                    right_field_id = link.target_field_ids[i]

                    left_field = self.__field_details.get(left_field_id)
                    right_field = self.__field_details.get(right_field_id)

                    if not left_field or not right_field:
                        continue

                    join_conditions.append({
                        "left_field_id": left_field.id,
                        "left_dataset_id": left_field.asset_id,
                        "left_field": left_field.sql_code,
                        "left_dataset": left_field.asset_name,
                        "left_sql_code": left_field.sql_code,
                        "right_field_id": right_field.id,
                        "right_dataset_id": right_field.asset_id,
                        "right_field": right_field.sql_code,
                        "right_dataset": right_field.asset_name,
                        "right_sql_code": right_field.sql_code,
                    })
            _tmp_join[_key]["fields"] = join_conditions

        return _tmp_join

    # GENERATE CALCULATED SQL CODES AND UPDATE SQL CODE IN FIELD ASSETS
    def __update_sql_code(self, field_id: int):
        field = self.__field_details[field_id]
        sql_code = field.sql_code

        # Find all matches
        matches = re.findall(self.__sql_code_regex_pattern, sql_code)

        if len(matches) <= 0:
            return sql_code

        # Use re.sub with a counter to replace each match with the corresponding element from the replacements list
        for match in matches:
            _field_id = int(match[0])
            replacement_sql_code = self.__update_sql_code(_field_id)
            sql_code = re.sub(
                self.__sql_code_regex_pattern,
                replacement_sql_code,
                sql_code,
                count=1,
            )

        self.__field_details[field_id].sql_code = sql_code
        return sql_code

    def __add_assets(self, field: FieldsModel, field_details: FieldDetailsModel, overwite: bool = False):
        asset_id = field_details.asset_id
        self.__assets.add(asset_id)
        if field.join_opt is not None and (overwite or asset_id not in self.__assets_join_opt):
            self.__assets_join_opt[str(asset_id)] = field.join_opt

    def __update_calcuated_field_base_field(self, field_id: int, base_field: FieldsModel):
        """
        Converts recursive calculated_fields to base fields
        Base field is used to pass the join options
        """
        field = self.__field_details[field_id]
        sql_code = field.sql_code

        if field.type != FieldType.calculated_field:
            self.__add_assets(base_field, field)

        matches = re.findall(self.__sql_code_regex_pattern, sql_code)

        # FIXME make it better @{}[]
        if len(matches) <= 0:
            return f"@{{{field.id}}}[{field.name}]"

        for match in matches:
            _field_id = int(match[0])
            # FIXME make it better @{}[]
            pattern = f"@{{{match[0]}}}[{match[1]}]"
            replacement_sql_code = self.__update_calcuated_field_base_field(_field_id, base_field)
            sql_code = sql_code.replace(pattern, replacement_sql_code)

        self.__field_details[field_id].sql_code = f"{sql_code}"

        return f"({sql_code})"

    def __add_field(self, field: FieldsModel):
        field_id = field.id
        field_detail = self.__field_details[field_id]

        sql_code = field.sql_code
        if sql_code is None:
            sql_code = field_detail.sql_code

        selected_field = {
            "dataset": field_detail.asset_name,
            "field": field_detail.name,
            "sql_code": sql_code,
            "measure_func": field.measure_func,
            "renameCol": field.name,
            "dimension_func": field.dimension_func,
        }

        if field_detail.is_pii and not self.__can_view_pii:
            selected_field["isFunction"] = True
            selected_field["function"] = [
                {
                    "funName": "custom",
                    "params": {"expr": f"MD5({field_detail.sql_code})"},
                }
            ]

        # FIXME Need to update query generator Needed function on function for this functionality
        if field.dimension_func is not None:
            selected_field["isFunction"] = True
            selected_field["function"] = [
                {
                    "funName": field.dimension_func,
                    "params": {"expr": field_detail.sql_code},
                }
            ]

        # Override if measure
        if field.category != CategoryType.measure:
            self.__data_categories["dimension"].append(field_id)
        else:
            self.__data_categories["measure"].append(field_id)
            selected_field["isFunction"] = True
            selected_field["function"] = [
                {
                    "funName": field.measure_func,
                    "params": {"expr": field_detail.sql_code},
                }
            ]

        self.__selected_fields.append(selected_field)

    def build_cte(self):
        cte_builder = CTE(
            self.__join,
            self.__etl,
            self.__field_details,
            SmartQueryGenerator,
            self.__field_details_fetcher,
            self.__links,
            self.__can_view_pii,
            self.__uniqueness_threshold,
            self.__sql_code_regex_pattern,
        )
        cte_builder.build()

        self.__ctes = cte_builder.get_ctes()
        self.__etl = cte_builder.get_etl()
        self.__field_details = cte_builder.get_field_details()
        self.__links = cte_builder.get_links()

    def build_assets_filter_sort(self):
        _filter = Filter(self.__etl.filter, self.__field_details, self.__can_view_pii)
        _filter.build_filters()
        assets = _filter.get_assets()
        for asset in assets:
            self.__assets.add(asset)

        if self.__etl.filter is not None:
            for sort in self.__etl.filter.sort_by:
                field = self.__field_details[sort.id]
                self.__assets.add(field.asset_id)

    def build_calculated_field_base_field(self):
        for field in self.__etl.fields:
            if field.type == FieldType.calculated_field:
                self.__update_calcuated_field_base_field(field.id, field)
            else:
                _f = self.__field_details[field.id]
                self.__add_assets(field, _f, True)

    def build_calculated_field_sql_codes(self):
        for field in self.__etl.fields:
            self.__update_sql_code(field.id)

    def build_fields(self):
        for field in self.__etl.fields:
            self.__add_field(field)

    def build_join(self, join: Optional[dict] = None):
        if join is None:
            for _field in self.__etl.fields:
                if _field.sql_code is not None:
                    continue
                _f = self.__field_details[_field.id]

                # if _f.type != FieldType.calculated_field:
                #     self.__add_assets(_field, _f, True)

            selected_fields = set(self.__field_details.keys())
            _join = Join(self.__links, selected_fields)
            join = _join.get_join_json(list(self.__assets), self.__assets_join_opt)

        fields = Join.get_fields(join, self.__links)

        for field in fields:
            field_details_keys = self.__field_details.keys()
            if field not in field_details_keys:
                self.__fetch_fields_details(fields)
                break

        self.__join = join

    def build_join_json(self):
        __join_json = self.__get_join_names(self.__join)
        self.__join_json = __join_json

    def build_filters(self):
        _filter = Filter(self.__etl.filter, self.__field_details, self.__can_view_pii)
        self.__filters = _filter.get_fresh_filter()

    def build_group_by(self):
        group_by = GroupBy(self.__etl, self.__field_details, self.__data_categories)
        group_by.build()
        self.__group_by = group_by.get_group_by()

    def build_sort_fields(self):
        sort_by = []

        # fields: dict[FieldsModel] = {}
        # for _field in self.__etl.fields:
        #     fields[_field.id] = _field

        for sort in self.__etl.filter.sort_by:
            sort_by_json = {
                "direction": sort.direction,
                # "renameCol": fields[sort.id].name,
                # "renameCol": sort.alias,
            }

            if sort.alias is not None:
                sort_by_json["renameCol"] = sort.alias
            else:
                sort_by_json["dataset"] = self.__field_details[sort.id].asset_name
                sort_by_json["field"] = self.__field_details[sort.id].name

            sort_by.append(sort_by_json)

        self.__sort_fields = sort_by

    def build_limit(self):
        self.__limit = self.__etl.filter.limit

    def build_offset(self):
        self.__offset = self.__etl.filter.offset

    def build(self, cte=True):
        if len(self.__etl.fields) <= 0:
            return
        self.build_calculated_field_base_field()
        self.build_assets_filter_sort()
        self.build_join(self.__etl.join)
        if cte:
            self.build_cte()
        self.build_calculated_field_sql_codes()
        self.build_join_json()
        self.build_fields()
        self.build_group_by()

        if self.__etl.filter is not None:
            self.build_filters()
            self.build_sort_fields()
            self.build_limit()
            self.build_offset()

    def __generate_query(self):
        query_generate_json = QueryGeneratorModel(
            selected_fields=self.__selected_fields,
            join=self.__join_json,
            filters=self.__filters,
            groupby=self.__group_by,
            sort_fields=self.__sort_fields,
            limit=self.__limit,
            offset=self.__offset,
        )

        query = QueryGenerator().getQuery(query_generate_json)
        return query

    def prepare_query(self):
        self.__ctes.append((None, self.__generate_query()))

    def get_query(self):
        self.prepare_query()

        if len(self.__ctes) == 1:
            _, _query = self.__ctes[0]
            return _query

        final_query = ""
        ctes = []
        caller_query = ""
        for _name, _query in self.__ctes:
            if _name is None:
                caller_query = _query
                continue
            ctes.append(f"{_name} as ( {_query} )")

        final_query = f"WITH {', '.join(ctes)} {caller_query}"

        return final_query

    def get_join(self):
        return self.__join

    def get_field_details(self):
        return self.__field_details
