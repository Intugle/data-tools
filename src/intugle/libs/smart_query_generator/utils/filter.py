from copy import deepcopy

from ..models.models import FieldDetailsModel, FilterModel, WildCardOptions

STRING_OPERATOR = [
    WildCardOptions.starts_with,
    WildCardOptions.ends_with,
    WildCardOptions.contains,
    WildCardOptions.exactly_matches,
]

INITIAL_FILTERS = {"fields": [], "condition": "AND"}


class Filter:
    def __init__(
        self,
        filter: FilterModel,
        field_details: dict[int | str, FieldDetailsModel],
        can_view_pii: bool = True,
    ):
        self._filters = deepcopy(INITIAL_FILTERS)
        self._filter = filter
        self._field_details = field_details
        self._can_view_pii = can_view_pii
        self._assets = set()

    def _get_wildcard_value(self, option: WildCardOptions, value):
        if option == WildCardOptions.starts_with:
            return f"{value}%"
        if option == WildCardOptions.ends_with:
            return f"%{value}"
        if option == WildCardOptions.contains:
            return f"%{value}%"
        if option == WildCardOptions.exactly_matches:
            return value
        return value

    def _get_wildcard_operator(self, option: WildCardOptions, exclude):
        # if option == WildCardOptions.starts_with:
        #     return "like"
        if option in STRING_OPERATOR:
            if exclude:
                return "not_like"
            return "like"
        return option

    def build_selection(self):
        _filter = self._filter
        if _filter is not None and _filter.selections:
            selections = []
            for selection in _filter.selections:
                field = self._field_details[selection.id]
                fields = []

                self._assets.add(field.asset_id)

                if selection.values:
                    sel = {
                        "dataset": field.asset_name,
                        "field": field.name,
                        "sql_code": field.sql_code,
                        "operator": "not_in" if selection.exclude else "in",
                        "md5_hash": field.is_pii and not self._can_view_pii,
                        "params": {"value": selection.values, "type": "list"},
                    }
                    if selection.dimFunc:
                        sel["isFunction"] = True
                        sel["function"] = [{"funName": selection.dimFunc, "params": {"expr": field.sql_code}}]
                    fields.append(sel)

                if selection.null:
                    sel_null = {
                        "dataset": field.asset_name,
                        "field": field.name,
                        "sql_code": field.sql_code,
                        "operator": "is_not_null" if selection.exclude else "is_null",
                        "md5_hash": field.is_pii and not self._can_view_pii,
                        "params": {"value": "", "type": "list"},
                    }
                    if selection.dimFunc:
                        sel_null["isFunction"] = True
                        sel_null["function"] = [{"funName": selection.dimFunc, "params": {"expr": field.sql_code}}]
                    fields.append(sel_null)

                selections.append({
                    "fields": fields,
                    "condition": "AND" if selection.exclude else "OR",
                })

            self._filters["fields"].extend(selections)

    def build_wildcard(self):
        _filter = self._filter
        if _filter is not None and _filter.wildcards:
            wildcards = []
            for wildcard in _filter.wildcards:
                field = self._field_details[wildcard.id]

                self._assets.add(field.asset_id)

                value = self._get_wildcard_value(wildcard.option, wildcard.value)
                operator = self._get_wildcard_operator(wildcard.option, wildcard.exclude)
                wc = {
                    "dataset": field.asset_name,
                    "field": field.name,
                    "sql_code": field.sql_code,
                    "operator": operator,
                    "md5_hash": field.is_pii and not self._can_view_pii,
                    "params": {"value": value},
                }
                if wildcard.dimFunc:
                    wc["isFunction"] = True
                    wc["function"] = [
                        {
                            "funName": wildcard.dimFunc,
                            "params": {"expr": field.sql_code},
                        }
                    ]
                wildcards.append(wc)

            self._filters["fields"].extend(wildcards)

    def get_filter(self):
        return self._filters

    def build_filters(self):
        if self._filter is not None:
            self.build_selection()
            self.build_wildcard()

    def destroy_filters(self):
        self._filters = deepcopy(INITIAL_FILTERS)

    def get_fresh_filter(self):
        self.destroy_filters()
        self.build_filters()
        return self.get_filter()

    def get_assets(self):
        return self._assets
