from .transformation import Transformations
from .utils import get_formatted_dataset_field


class Operators:
    @classmethod
    def _in(cls, field, value, **_):
        return "{} IN {}".format(field, tuple(value))

    @classmethod
    def _not_in(cls, field, value, **_):
        return "{} NOT IN {}".format(field, tuple(value))

    @classmethod
    def _like(cls, field, value, **_):
        return "{} LIKE {}".format(field, value)

    @classmethod
    def _equals(cls, field, value, **_):
        return "{} = {}".format(field, value)

    @classmethod
    def _not_equals(cls, field, value, **_):
        return "{} != {}".format(field, value)

    @classmethod
    def _greater_than(cls, field, value, **_):
        return "{} > {}".format(field, value)

    @classmethod
    def _less_than(cls, field, value, **_):
        return "{} < {}".format(field, value)

    @classmethod
    def _greater_than_equal_to(cls, field, value, **_):
        return "{} >= {}".format(field, value)

    @classmethod
    def _less_than_equal_to(cls, field, value, **_):
        return "{} <= {}".format(field, value)

    @classmethod
    def _is_null(cls, field, **_):
        return "{} IS NULL".format(field)

    @classmethod
    def _is_not_null(cls, field, **_):
        return "{} IS NOT NULL".format(field)

    @classmethod
    def _between(cls, field, lowerValue, upperValue, **_):
        return "{} BETWEEN {} AND {}".format(field, lowerValue, upperValue)

    # FIXME is too messy review logic
    @classmethod
    def operator_factory(cls, filterField):
        md5_hash = filterField.get("md5_hash", False)
        params = filterField["params"]
        func = getattr(cls, "_" + filterField["operator"])
        typ = params.get("type", "string")
        isFunction = filterField.get("isFunction", False)
        function = filterField.get("function", None)

        if typ == "dataset_field":
            params["value"] = params["value"].get("sql_code", None)
            if params["value"] is None:
                params["value"] = get_formatted_dataset_field(
                    params["value"]["dataset"], params["value"]["dataset"]
                )
        if typ == "string":
            value = params.get("value", "")
            params["value"] = f"'{value}'"

        dataset_field = filterField.get("sql_code", None)
        if dataset_field is None:
            dataset_field = get_formatted_dataset_field(
                filterField["dataset"], filterField["field"]
            )

        # if fieldType == "calculated_field":
        #     dataset_field = filterField["field"]
        # else:
        #     dataset_field = get_formatted_dataset_field(filterField["dataset"], filterField["field"])

        if isFunction is True and function is not None:
            # func = functions[field["function"][0]["funName"]]
            transFunc = getattr(Transformations, function[0]["funName"])
            dataset_field = transFunc(**function[0]["params"])

        if md5_hash:
            dataset_field = f"MD5({dataset_field})"

        return func(dataset_field, **params)
