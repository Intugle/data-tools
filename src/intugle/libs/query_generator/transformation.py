class Transformations:
    # Aggregate Functions
    @classmethod
    def aggregate(cls, expr):
        return expr

    # Type Conversions
    @classmethod
    def toInt(cls, colm):
        return "int({})".format(colm)

    @classmethod
    def toBigInt(cls, colm):
        return "bigint({})".format(colm)

    @classmethod
    def toFloat(cls, colm):
        return "float({})".format(colm)

    @classmethod
    def toDouble(cls, colm):
        return "double({})".format(colm)

    @classmethod
    def toDate(cls, colm):
        return "date({})".format(colm)

    @classmethod
    def toBoolean(cls, colm):
        return "boolean({})".format(colm)

    @classmethod
    def toString(cls, colm):
        return "string({})".format(colm)

    # String Functions
    @classmethod
    def concat(cls, colmns: list):
        return "concat({})".format(",".join(colmns))

    @classmethod
    def concat_ws(cls, sep: str, colmns: list):
        return "concat_ws('{}',{})".format(sep, ",".join(colmns))

    @classmethod
    def trim(cls, colm):
        return "trim({})".format(colm)

    @classmethod
    def ltrim(cls, colm):
        return "ltrim({})".format(colm)

    @classmethod
    def rtrim(cls, colm):
        return "rtrim({})".format(colm)

    @classmethod
    def upper(cls, colm):
        return "upper({})".format(colm)

    @classmethod
    def capitalize(cls, colm):
        return "initcap({})".format(colm)

    @classmethod
    def lower(cls, colm):
        return "lower({})".format(colm)

    @classmethod
    def length(cls, colm):
        return "length({})".format(colm)

    @classmethod
    def right(cls, colm, length: int):
        return "right({}, {})".format(colm, length)

    @classmethod
    def left(cls, colm, length: int):
        return "left({}, {})".format(colm, length)

    @classmethod
    def coalesce(cls, exprs: list):
        return "coalesce({})".format(",".join(exprs))

    @classmethod
    def replace(cls, colm, search: str, replace: str = ""):
        if replace == "":
            return "replace({}, {})".format(colm, search)
        return "replace({}, {}, {})".format(colm, search, replace)

    @classmethod
    def reverse(cls, colm):
        return "reverse({})".format(colm)

    # Numeric Functions

    @classmethod
    def absolute(cls, colm):
        return "abs({})".format(colm)

    @classmethod
    def average(cls, expr):
        return "avg({})".format(expr)

    @classmethod
    def ceil(cls, colm):
        return "ceil({})".format(colm)

    @classmethod
    def floor(cls, colm):
        return "floor({})".format(colm)

    @classmethod
    def maximum(cls, colm):
        return "max({})".format(colm)

    @classmethod
    def mean(cls, colm):
        return "mean({})".format(colm)

    @classmethod
    def minimum(cls, colm):
        return "min({})".format(colm)

    @classmethod
    def modulus(cls, expr1, expr2):
        return "mod({}, {})".format(expr1, expr2)

    @classmethod
    def negative(cls, expr):
        return "negative({})".format(expr)

    @classmethod
    def power(cls, expr1, expr2):
        return "power({}, {})".format(expr1, expr2)

    @classmethod
    def round(cls, expr, decimal):
        return "round({}, {})".format(expr, decimal)

    @classmethod
    def square_root(cls, expr):
        return "sqrt({})".format(expr)

    @classmethod
    def stddev(cls, expr):
        return "stddev({})".format(expr)

    @classmethod
    def sum(cls, expr):
        return "sum({})".format(expr)

    @classmethod
    def variance(cls, expr):
        return "variance({})".format(expr)

    @classmethod
    def count(cls, expr):
        return "count({})".format(expr)

    @classmethod
    def countDistinct(cls, expr):
        return "count(distinct {})".format(expr)

    @classmethod
    def currentDate(cls):
        return "current_date()"

    @classmethod
    def day(cls, expr):
        return "day({})".format(expr)

    @classmethod
    def month(cls, expr):
        return "month({})".format(expr)

    @classmethod
    def year(cls, expr):
        return "year({})".format(expr)

    @classmethod
    def yearMonth(cls, expr):
        return "date_format({}, 'yyyy-MM')".format(expr)

    @classmethod
    def currentTimestamp(cls, expr):
        return "current_timestamp({})".format(expr)

    @classmethod
    def dateFormat(cls, expr, dt_format):
        return "date_format({}, '{}')".format(expr, dt_format)

    # Modifier Functions

    @classmethod
    def distinct(cls, expr):
        return "distinct {}".format(expr)

    @classmethod
    def custom(cls, expr):
        return "{}".format(expr)
