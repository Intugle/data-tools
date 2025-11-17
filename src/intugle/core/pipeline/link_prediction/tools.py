from threading import Lock
from typing import TYPE_CHECKING, Annotated, Dict, List, Optional, Tuple

import pandas as pd

from langchain_core.tools import StructuredTool
from langgraph.prebuilt import InjectedState

from intugle.adapters.adapter import Adapter
from intugle.analysis.models import DataSet
from intugle.core.pipeline.link_prediction.schemas import Link, OutputSchema, ValiditySchema

if TYPE_CHECKING:
    from intugle.models.resources.model import PrimaryKey


class LinkPredictionTools:
    UNIQUENESS_THRESHOLD = 0.8
    INTERSECTION_THRESHOLD = 0.7

    def __init__(
        self,
        profiling_data: pd.DataFrame,
        datasets: Dict[str, DataSet],
        adapter: Adapter,
    ):
        self._profiling_data = profiling_data
        self._links: Dict[tuple, Dict[str, OutputSchema]] = {}
        self._datasets = datasets
        self._adapter = adapter
        self._lock = Lock()

    def _check_table_and_column_presence(
        self, table_name: str, column_name: str
    ) -> str | bool:
        """
        Check whether the table name and column name provided by llm are valid or not
        Args:
            table_name (str): table name
            column_name (str): column name

        Returns:
            Union[str, bool]: True if the column name and table name are valid else a validation message is sent
        """
        condn1 = self._profiling_data.upstream_table_name == table_name
        if not condn1.any():
            return f"`{table_name}` is not a valid table name"
        cond2 = self._profiling_data.upstream_column_name == column_name
        if not ((condn1 & cond2).any()):
            avaliable_columns = ",".join(
                map(
                    lambda col: f"`{col}`",
                    self._profiling_data.loc[condn1, "upstream_column_name"].to_list(),
                )
            )
            return f"`{table_name}` table doesnot have column called `{column_name}` only {avaliable_columns} columns are present"
        return True

    def _check_table_column(self, link: Link) -> ValiditySchema:
        """
        Check the table name and column name in a llm provided link
        Args:
            link (Link): Link provided by llm
        Returns:
            Union[str, bool]: True if the column name and table name are valid else a validation message is sent
        """
        checkA_1 = self._check_table_and_column_presence(link.table1, link.column1)
        checkA_2 = self._check_table_and_column_presence(link.table2, link.column2)
        feedbacks = []
        for check in [checkA_1, checkA_2]:
            if isinstance(check, str):
                feedbacks.append(f"- {check}")

        if len(feedbacks) == 0:
            valid = True
            message = "- Table name and Column Names are valid"
        else:
            valid = False
            message = "\n".join(feedbacks)
        return ValiditySchema(message=message, valid=valid)

    def _datatype_check(self, link: Link) -> ValiditySchema:
        """
        Check whether the column datatype is matching or not in the ling
        Args:
            link (Link): Link provided by llm

        Returns:
            Union[str, bool]: True if the datatype are valid else a validation message is sent
        """
        dtype1 = self._profiling_data.loc[
            (self._profiling_data.upstream_table_name == link.table1)
            & (self._profiling_data.upstream_column_name == link.column1),
            "datatype_l1",
        ].values[0]
        dtype2 = self._profiling_data.loc[
            (self._profiling_data.upstream_table_name == link.table2)
            & (self._profiling_data.upstream_column_name == link.column2),
            "datatype_l1",
        ].values[0]

        msg = "- Datatypes between columns are valid."
        valid = True
        if dtype1 != dtype2:
            msg = f"Datatype of column `{link.column1}` in table `{link.table1}` is {dtype1} which doesnot match with datatype of column `{link.column2}` in table `{link.table2}`  which is {dtype2}."
            valid = False
        return ValiditySchema(message=msg, valid=valid)

    def _uniqueness_check_single(self, link: Link) -> ValiditySchema:
        """
        Check if the link provided llm the uniqueness of column is matching the threshold or not
        Args:
            link (Link): Link provided by llm

        Returns:
            Union[str, bool]: True if uniqueness threshold is met else validation message is sent.
        """
        uniqueness_ratio_1 = self._profiling_data.loc[
            (self._profiling_data["upstream_table_name"] == link.table1)
            & (self._profiling_data["upstream_column_name"] == link.column1),
            "uniqueness_ratio",
        ].values[0]

        uniqueness_ratio_2 = self._profiling_data.loc[
            (self._profiling_data["upstream_table_name"] == link.table2)
            & (self._profiling_data["upstream_column_name"] == link.column2),
            "uniqueness_ratio",
        ].values[0]

        # Optionally, you can calculate the overall max uniqueness
        max_uniqueness = max(uniqueness_ratio_1, uniqueness_ratio_2)

        msg = f"Uniqueness of column `{link.column1}` in table `{link.table1}` is {uniqueness_ratio_1 * 100:.2f} percent, and the uniqueness of `{link.column2}` in table `{link.table2}` is {uniqueness_ratio_2 * 100:.2f} percent"
        if max_uniqueness < LinkPredictionTools.UNIQUENESS_THRESHOLD:
            msg += ", This is lower than the acceptable limit."
            valid = False
        else:
            msg += ", This uniqueness is within acceptable limit"
            valid = True
    
        return ValiditySchema(
            message=msg,
            valid=valid,
            extra={
                "uniqueness_ratios": {
                    "from_uniqueness_ratio": uniqueness_ratio_1,
                    "to_uniqueness_ratio": uniqueness_ratio_2,
                }
            },
        )
    
    def _uniquesness_check_composite(
        self, links: list[Link]
    ) -> ValiditySchema | Tuple[ValiditySchema, dict]:
        """
        Check if the link provided llm the uniqueness of column is matching the threshold or not
        Args:
            links (Link): Composite Link provided by llm

        Returns:
            Union[str, bool]: True if uniqueness threshold is met else validation message is sent.
        """
        link = links[0]  # Get first link to determine tables

        table1_name = link.table1
        table2_name = link.table2
        
        table1_dataset = self._datasets[table1_name]
        table2_dataset = self._datasets[table2_name]

        table1_columns = [lnk.column1 for lnk in links]
        table2_columns = [lnk.column2 for lnk in links]

        # Check for pre-computed distinct_count in PrimaryKey model
        count_distinct_composite1 = None
        table1_pk: Optional[PrimaryKey] = table1_dataset.source.table.key
        if table1_pk and sorted(table1_pk.columns) == sorted(table1_columns) and table1_pk.distinct_count is not None:
            count_distinct_composite1 = table1_pk.distinct_count
        else:
            # Fallback to adapter if not pre-computed
            count_distinct_composite1 = self._adapter.get_composite_key_uniqueness(
                table_name=table1_name, columns=table1_columns, dataset_data=table1_dataset.data
            )

        count_distinct_composite2 = None
        table2_pk: Optional[PrimaryKey] = table2_dataset.source.table.key
        if table2_pk and sorted(table2_pk.columns) == sorted(table2_columns) and table2_pk.distinct_count is not None:
            count_distinct_composite2 = table2_pk.distinct_count
        else:
            # Fallback to adapter if not pre-computed
            count_distinct_composite2 = self._adapter.get_composite_key_uniqueness(
                table_name=table2_name, columns=table2_columns, dataset_data=table2_dataset.data
            )

        table1_total_count = self._profiling_data.loc[self._profiling_data['upstream_table_name'] == table1_name, 'count'].iloc[0]
        table2_total_count = self._profiling_data.loc[self._profiling_data['upstream_table_name'] == table2_name, 'count'].iloc[0]

        uniqueness_composite1 = count_distinct_composite1 / table1_total_count if table1_total_count > 0 else 0
        uniqueness_composite2 = count_distinct_composite2 / table2_total_count if table2_total_count > 0 else 0

        max_uniqueness = max(uniqueness_composite1, uniqueness_composite2)

        table1_col_list = ", ".join(table1_columns)
        table2_col_list = ", ".join(table2_columns)

        msg = f"Uniqueness of combined columns `{table1_col_list}` in table `{link.table1}` is {uniqueness_composite1 * 100:.2f} percent, and the uniqueness of `{table2_col_list}` in table `{link.table2}` is {uniqueness_composite2 * 100:.2f} percent"
        if max_uniqueness < LinkPredictionTools.UNIQUENESS_THRESHOLD:
            msg += ", This is lower than the acceptable limit"
            valid = False
            return ValiditySchema(message=msg, valid=valid)
        else:
            msg += ", This uniqueness is within acceptable limit"
            valid = True
            return ValiditySchema(
                message=msg,
                valid=valid,
                extra={
                    "uniqueness_ratios": {
                        "from_uniqueness_ratio": uniqueness_composite1,
                        "to_uniqueness_ratio": uniqueness_composite2,
                    }
                },
            ), {
                "count_distinct_composite1": count_distinct_composite1,
                "count_distinct_composite2": count_distinct_composite2,
            }

    def _intersection_count_check(self, links: list[Link], **kwargs) -> ValiditySchema:
        """
        Does intersection count validation for both single and multi link
        Args:
            links (list[Link]): Link provided by llm

        Returns:
            Union[str, bool]: True if intersection is valid else validity message is sent
        """

        table1_name = links[0].table1
        table2_name = links[0].table2
        
        table1_dataset = self._datasets[table1_name]
        table2_dataset = self._datasets[table2_name]

        if len(links) == 1:
            link = links[0]

            count_distinct_col1 = self._profiling_data.loc[
                (self._profiling_data["upstream_table_name"] == link.table1)
                & (self._profiling_data["upstream_column_name"] == link.column1),
                "distinct_value_count",
            ].values[0]

            count_distinct_col2 = self._profiling_data.loc[
                (self._profiling_data["upstream_table_name"] == link.table2)
                & (self._profiling_data["upstream_column_name"] == link.column2),
                "distinct_value_count",
            ].values[0]

            intersect_count = self._adapter.intersect_count(
                table1=table1_dataset,
                column1_name=link.column1,
                table2=table2_dataset,
                column2_name=link.column2
            )

            if intersect_count == 0:
                return ValiditySchema(
                    message=f"The intersection between `{link.column1}` column in table `{link.table1}` with column `{link.column2}` in table `{link.table2}` resulted in zero rows",
                    valid=False,
                )

            intersect_ratio_col1 = intersect_count / count_distinct_col1 if count_distinct_col1 > 0 else 0
            intersect_ratio_col2 = intersect_count / count_distinct_col2 if count_distinct_col2 > 0 else 0

            msg1 = f"{intersect_ratio_col1 * 100:.2f} percent of values in `{link.column1}` in table `{link.table1}` matched with `{link.column2}` in table `{link.table2}`."
            msg2 = f"{intersect_ratio_col2 * 100:.2f} percent of values in `{link.column2}` in table `{link.table2}` matched with `{link.column1}` in table `{link.table1}`."
            if (
                max(intersect_ratio_col1, intersect_ratio_col2)
                < LinkPredictionTools.INTERSECTION_THRESHOLD
            ):
                error_msg1 = f"- Only {msg1}"
                error_msg2 = f"- Only {msg2}"
                return ValiditySchema(
                    message=f"{error_msg1}\n{error_msg2}, This is lower than acceptable threshold",
                    valid=False,
                )

            return ValiditySchema(
                message=f"{msg1}\n{msg2}",
                valid=True,
                extra={
                    "link": {
                        "links": links,
                        "intersect_count": intersect_count,
                        "intersect_ratio_col1": intersect_ratio_col1,
                        "intersect_ratio_col2": intersect_ratio_col2,
                        "from_uniqueness_ratio": kwargs.get("from_uniqueness_ratio"),
                        "to_uniqueness_ratio": kwargs.get("to_uniqueness_ratio"),
                    }
                },
            )

        else:
            # Multiple links - composite key check
            table1_columns = [lnk.column1 for lnk in links]
            table2_columns = [lnk.column2 for lnk in links]

            count_distinct_composite1 = kwargs.get("count_distinct_composite1")
            count_distinct_composite2 = kwargs.get("count_distinct_composite2")

            intersect_count = self._adapter.intersect_composite_keys_count(
                table1=table1_dataset,
                columns1=table1_columns,
                table2=table2_dataset,
                columns2=table2_columns,
            )

            composite_key1 = f"({', '.join(table1_columns)})"
            composite_key2 = f"({', '.join(table2_columns)})"

            if intersect_count == 0:
                return ValiditySchema(
                    message=f"The intersection between composite key {composite_key1} in table `{table1_name}` with composite key {composite_key2} in table `{table2_name}` resulted in zero rows",
                    valid=False,
                )

            intersect_ratio_col1 = intersect_count / count_distinct_composite1 if count_distinct_composite1 > 0 else 0
            intersect_ratio_col2 = intersect_count / count_distinct_composite2 if count_distinct_composite2 > 0 else 0

            msg1 = f"-{intersect_ratio_col1 * 100:.2f} percent of composite key {composite_key1} values in table `{table1_name}` matched with {composite_key2} in table `{table2_name}`."
            msg2 = f"-{intersect_ratio_col2 * 100:.2f} percent of composite key {composite_key2} values in table `{table2_name}` matched with {composite_key1} in table `{table1_name}`."
            if (
                max(intersect_ratio_col1, intersect_ratio_col2)
                < LinkPredictionTools.INTERSECTION_THRESHOLD
            ):
                error_msg1 = f"- Only {msg1}"
                error_msg2 = f"- Only {msg2}"
                return ValiditySchema(
                    message=f"{error_msg1}\n{error_msg2}, This is lower than acceptable threshold.",
                    valid=False,
                )

            return ValiditySchema(
                message=f"{msg1}\n{msg2}",
                valid=True,
                extra={
                    "link": {
                        "links": links,
                        "intersect_count": intersect_count,
                        "intersect_ratio_col1": intersect_ratio_col1,
                        "intersect_ratio_col2": intersect_ratio_col2,
                        "from_uniqueness_ratio": kwargs.get("from_uniqueness_ratio"),
                        "to_uniqueness_ratio": kwargs.get("to_uniqueness_ratio"),
                    }
                },
            )

    def _single_link_validity(
        self, link: Link
    ) -> str | Tuple[str, ValiditySchema]:
        checks = []
        # Table, Column presence check
        check1 = self._check_table_column(link=link)
        if not check1.valid:
            return check1.message

        checks.append(check1.message)

        # Datatype check
        check2 = self._datatype_check(link=link)
        if not check2.valid:
            return check2.message

        checks.append(check2.message)

        # Uniqueness check
        check3 = self._uniqueness_check_single(link=link)
        if not check3.valid:
            return check3.message

        checks.append(check3.message)

        uniqueness_ratios = check3.extra.get("uniqueness_ratios", {})

        # Intersection check
        check4 = self._intersection_count_check(links=[link], **uniqueness_ratios)
        if not check4.valid:
            return check4.message

        checks.append(check4.message)

        return "\n---\n".join(checks), check4

    def _multi_link_validity(
        self, links: List[Link]
    ) -> str | Tuple[str, ValiditySchema]:
        checks = []

        # Check for table column name
        checks_1 = list(
            filter(
                lambda check: not check.valid,
                list(map(self._check_table_column, links)),
            )
        )
        if len(checks_1) != 0:
            return "\n\n".join([check.message for check in checks_1])

        checks.append("- Table name and Column names are valid.")

        # Datatype check
        checks_2 = list(
            filter(
                lambda check: not check.valid,
                list(map(self._datatype_check, links)),
            )
        )
        if len(checks_2) != 0:
            return "\n\n".join([check.message for check in checks_2])

        checks.append("- Datatype between columns are also matching.")

        # Uniqueness Check
        checks_3 = self._uniquesness_check_composite(links=links)
        if not isinstance(checks_3, tuple) and not checks_3.valid:
            return checks_3.message

        schema, count_metrics = checks_3
        uniqueness_ratios = schema.extra.get("uniqueness_ratios", {})

        checks.append(schema.message)

        # Intersection count
        checks_4 = self._intersection_count_check(
            links=links, **count_metrics, **uniqueness_ratios
        )
        if not checks_4.valid:
            return checks_4.message

        checks.append(checks_4.message)

        return "\n---\n".join(checks), checks_4

    def _id_creator(self, links: List[Link]) -> str:
        links = [f"{lnk.table1}.{lnk.column1}" for lnk in links] + [
            f"{lnk.table2}.{lnk.column2}" for lnk in links
        ]
        return "$$##$$".join(sorted(links))

    def save_links(
        self,
        links: Annotated[List[Link], "Links to save"],
        table1_name: Annotated[str, InjectedState("table1_name")],
        table2_name: Annotated[str, InjectedState("table2_name")],
    ) -> str:
        with self._lock:
            key = (table1_name, table2_name)
            _id_ = self._id_creator(links=links)
            if key in self._links:
                if _id_ in self._links[key]:
                    self._links[key][_id_].save = True
                    return "Link saved"
                else:
                    all_links = "\n".join(
                        [
                            f"- {str(link.model_dump()['links'])}"
                            for link in self._links[key].values()
                        ]
                    )
                    return f"""The links provided is not validated yet below are the links that have passed all the validations:\n{all_links}"""

            return "There are no links that have passed validation checks to be saved"

    def validity_check(
        self,
        table1_name: Annotated[str, InjectedState("table1_name")],
        table2_name: Annotated[str, InjectedState("table2_name")],
        links: Annotated[
            List[Link],
            "List of links to validate",
        ],
    ) -> dict:
        try:
            if len(links) == 1:
                response = self._single_link_validity(link=links[0])
            else:
                response = self._multi_link_validity(links=links)

            if isinstance(response, str):
                return response

            key = (table1_name, table2_name)
            res = {
                **response[1].extra["link"],
                "table1_name": table1_name,
                "table2_name": table2_name,
            }
            res = OutputSchema.model_validate(res)

            _id_ = self._id_creator(links)
            if key not in self._links:
                self._links[key] = {}

            self._links[key][_id_] = res

            return response[0]
        except Exception as ex:
            import traceback

            print(f"[!] Validity check: {traceback.format_exc()}")
            raise ex

    def get_tools(
        self,
    ) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                name="validity_check",
                func=self.validity_check,
                description="""Check the validity of links, this tool performs following validations:
                1. Validates the presence of column in the table.
                2. Checks the datatype of the columns that are linked.
                3. Checks the uniqueness of the columns whether or not it is meeting the mentioned threshold.
                4. Checks if the links are actually intersecting by getting how much data are getting mapped.

                ## How to use:
                -  Provide single link in the case where single pair of columns forms links.
                - Provide list of links in the case where composite keys forms links.
                """,
            ),
            StructuredTool.from_function(
                name="save_links",
                func=self.save_links,
                description="""
                Save any links you want after you have done all validity checks.
                ## How to use:
                -  Provide single link in the case where single pair of columns forms links.
                - Provide list of links in the case where composite keys forms links.
                - You can call this tool many times to store different links.
                """,
            ),
        ]
