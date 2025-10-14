from typing import Optional

from pydantic import BaseModel, Field

from .operators import Operators
from .transformation import Transformations
from .utils import get_formatted_dataset_field, get_formatted_name


class QueryGeneratorModel(BaseModel):
    selected_fields: list[dict] = Field(default_factory=list)
    join: dict = Field(default_factory=dict)
    filters: dict = Field(default_factory=dict)
    groupby: dict = Field(default_factory=dict)
    sort_fields: list[dict] = Field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None


# @dataclass_json
# @dataclass
# class QueryGeneratorConfig:
#     selected_fields: list[dict] = field(default_factory=list)
#     join: dict = field(default_factory=dict)
#     filters: dict = field(default_factory=dict)
#     groupby: dict = field(default_factory=dict)
#     sort_fields: list[dict] = field(default_factory=list)
#     limit: Optional[int] = None
#     offset: Optional[int] = None


class QueryGenerator:
    @classmethod
    def get_select_fields(cls, selectFields):
        # Extracting Select fields
        selectedFields = []

        if len(selectFields) == 0:
            selectedFieldsExpr = " * "
        else:
            for field in selectFields:
                isFunction = field.get("isFunction", None)
                if isFunction:
                    #         func = functions[field["function"][0]["funName"]]
                    func = getattr(Transformations, field["function"][0]["funName"])
                    expr = func(**field["function"][0]["params"])
                else:
                    expr = field.get("sql_code", None)
                    if expr is None:
                        expr = get_formatted_dataset_field(
                            field["dataset"], field["field"]
                        )

                renameCol = field.get("renameCol", None)
                if renameCol:
                    expr = f"{expr} as {get_formatted_name(renameCol)}"

                selectedFields.append(expr)
            selectedFieldsExpr = ", ".join(selectedFields)

        return selectedFieldsExpr

    @classmethod
    def get_join_expr(cls, joinFields):
        join_query = " FROM "
        # if len(joinFields) == 1:
        #     join_query += f" {joinFields['0']['dataset']} "
        #     return join_query
        tbl_cnt = len(joinFields)
        for _i in range(tbl_cnt):
            i = str(_i)
            if _i == 0:
                join_query += f"{get_formatted_name(joinFields[i]['dataset'])}"
            else:
                joining_cndns = []
                for join_col in joinFields[i]["fields"]:
                    left_sql_code = join_col.get("left_sql_code", None)
                    right_sql_code = join_col.get("right_sql_code", None)
                    if left_sql_code is None:
                        left_sql_code = get_formatted_dataset_field(
                            join_col["left_dataset"], join_col["left_field"]
                        )
                    if right_sql_code is None:
                        right_sql_code = get_formatted_dataset_field(
                            join_col["right_dataset"], join_col["right_field"]
                        )
                    joining_cndns.append(left_sql_code + " = " + right_sql_code)

                joining_cndn = " AND ".join(joining_cndns)

                join_query += (
                    " "
                    + joinFields[i].get("join_type", "").upper()
                    + " JOIN "
                    + f"{get_formatted_name(joinFields[i]['dataset'])}"
                    + " ON "
                    + str(joining_cndn)
                )
        return join_query

    @classmethod
    def _filter(cls, filter_fields):
        fields = filter_fields.get("fields", [])
        filter_cols = []
        for _field in fields:
            _fields = _field.get("fields", None)
            if _fields:
                expr = cls._filter(_field)
                expr = f"({expr})"
            else:
                expr = Operators.operator_factory(_field)
            filter_cols.append(expr)
        return " {} ".format(filter_fields["condition"].upper()).join(filter_cols)

    @classmethod
    def get_filter_expr(cls, filterFields):
        # Filter Expression
        filterExpr = ""
        if filterFields != {}:
            filter_cols = cls._filter(filterFields)
            if filter_cols:
                filterExpr = filterExpr + " WHERE " + filter_cols
        return filterExpr

    @classmethod
    def get_groupby_expr(cls, groupbyFields):
        groupbyExpr = ""
        if groupbyFields != {} and len(groupbyFields["keys"]) != 0:
            groupbyCols = []
            for field in groupbyFields["keys"]:
                # _dataset = field.get("dataset", None)
                # _field = field["field"]
                # if _dataset is not None:
                #     _dataset_field = get_formatted_dataset_field(_dataset, _field)
                # else:
                #     _dataset_field = f"{_field}"

                # _func = field.get("function", None)
                # if _func is not None:
                #     # FIXME temp fix
                #     _dataset_field = f"{_func}({_dataset_field})"
                renameCol = field.get("renameCol", None)
                if renameCol is not None:
                    _dataset_field = get_formatted_name(renameCol)
                else:
                    _dataset_field = field["sql_code"]
                groupbyCols.append(_dataset_field)

            groupbyExpr = " GROUP BY " + " , ".join(groupbyCols)

            if "having" in groupbyFields and len(groupbyFields["having"]) != 0:
                groupbyExpr += cls.get_filter_expr(groupbyFields["having"]).replace(
                    " WHERE ", " HAVING ", 1
                )
        return groupbyExpr

    @classmethod
    def get_sort_expr(cls, sortFields):
        # Sort Expression
        sortExpr = ""
        if sortFields != []:
            sortExpr = " ORDER BY "
            sortCols = []
            for sortField in sortFields:
                renameCol = sortField.get("renameCol", None)
                if renameCol is not None:
                    sortCol = get_formatted_name(renameCol)
                else:
                    sortCol = get_formatted_dataset_field(
                        sortField["dataset"], sortField["field"]
                    )

                direction = sortField.get("direction", "asc")
                if direction == "asc" or direction == "ascending":
                    sortOp = "ASC"
                elif direction == "desc" or direction == "descending":
                    sortOp = "DESC"
                else:
                    sortOp = ""
                sortCols.append(sortCol + " " + sortOp)
            sortExpr = sortExpr + " , ".join(sortCols)
        return sortExpr

    @classmethod
    def get_limit_expr(cls, limit):
        return " LIMIT {}".format(limit)

    @classmethod
    def get_offset_expr(cls, offset):
        return " OFFSET {}".format(offset)

    @classmethod
    def getQuery(cls, config: QueryGeneratorModel):
        sqlQuery = ""

        if config.selected_fields != []:
            sqlQuery += "SELECT "
            sqlQuery += cls.get_select_fields(config.selected_fields)
        else:
            return sqlQuery

        # From dataset
        # if "from" in config:
        #     sqlQuery = sqlQuery + " FROM " + f"{config['from']}"

        if config.join != {}:
            sqlQuery += cls.get_join_expr(config.join)

        if config.filters != {}:
            sqlQuery += cls.get_filter_expr(config.filters)

        if config.groupby != {}:
            sqlQuery += cls.get_groupby_expr(config.groupby)

        if config.sort_fields != []:
            sqlQuery += cls.get_sort_expr(config.sort_fields)

        if config.limit is not None:
            sqlQuery += cls.get_limit_expr(config.limit)

        if config.offset is not None:
            sqlQuery += cls.get_offset_expr(config.offset)

        return sqlQuery
