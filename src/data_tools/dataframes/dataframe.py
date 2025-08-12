from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from data_tools.core.pipeline.business_glossary.bg import BusinessGlossary
from data_tools.core.pipeline.datatype_identification.l2_model import L2Model
from data_tools.core.pipeline.datatype_identification.pipeline import DataTypeIdentificationPipeline
from data_tools.core.pipeline.key_identification.ki import KeyIdentificationLLM

from .models import (
    BusinessGlossaryOutput,
    ColumnGlossary,
    ColumnProfile,
    DataTypeIdentificationL1Output,
    DataTypeIdentificationL2Input,
    DataTypeIdentificationL2Output,
    KeyIdentificationOutput,
    ProfilingOutput,
)


class DataFrame(ABC):
    @abstractmethod
    def profile(self, df: Any) -> ProfilingOutput:
        pass

    @abstractmethod
    def column_profile(
        self,
        df: Any,
        table_name: str,
        column_name: str,
        sample_limit: int = 200,
    ) -> ColumnProfile:
        pass

    def datatype_identification_l1(
        self,
        df: Any,
        table_name: str,
        column_stats: dict[str, ColumnProfile],
    ) -> list[DataTypeIdentificationL1Output]:
        """
        Performs a Level 1 data type identification based on the column's profile.

        This initial step uses the `dtype_sample` collected during the column
        profiling to infer the most likely data type for the column.
        Args:
            df: The input DataFrame (not used in this generic implementation).
            table_name: The name of the table the column belongs to.
            column_stats: The pre-computed statistics for the column from the
                          `column_profile` method.

        Returns:
            A list of DataTypeIdentificationL1Output models, one for each column.
        """
        records = []
        for column_name, stats in column_stats.items():
            records.append({"table_name": table_name, "column_name": column_name, "values": stats.dtype_sample})

        l1_df = pd.DataFrame(records)
        di_pipeline = DataTypeIdentificationPipeline()
        l1_result = di_pipeline(sample_values_df=l1_df)
        output = [DataTypeIdentificationL1Output(**row) for row in l1_result.to_dict(orient="records")]

        return output

    def datatype_identification_l2(
        self,
        df: Any,
        table_name: str,
        column_stats: list[DataTypeIdentificationL2Input],
    ) -> list[DataTypeIdentificationL2Output]:
        """
        Performs a Level 2 data type identification based on the column profiling.

        Args:
            df: The input DataFrame (not used in this generic implementation).
            table_name: The name of the table (not used in this generic implementation).
            column_stats: The list of columns, sample data (DataTypeIdentificationL2Input).

        Returns:
            A list of DataTypeIdentificationL2Output models containing the inferred data type l2.
        """
        column_values_df = pd.DataFrame([item.model_dump() for item in column_stats])
        l2_model = L2Model()
        l2_result = l2_model(l1_pred=column_values_df)
        output = [DataTypeIdentificationL2Output(**row) for row in l2_result.to_dict(orient="records")]

        return output

    def key_identification(
        self,
        table_name: str,
        column_stats: pd.DataFrame,
    ) -> KeyIdentificationOutput:
        """
        Identifies potential primary keys in the DataFrame based on column profiles.

        Args:
            table_name: The name of the table the column belongs to.
            column_stats: The pre-computed statistics for the columns from the
                          `column_profile` method.

        Returns:
            A KeyIdentificationOutput model containing the identified primary key column.
        """
        ki_model = KeyIdentificationLLM(profiling_data=column_stats)
        ki_result = ki_model()
        output = KeyIdentificationOutput(**ki_result)
        return output

    def generate_business_glossary(
        self,
        table_name: str,
        column_stats: pd.DataFrame,
        domain: str = "",
    ) -> BusinessGlossaryOutput:
        """
        Generates business glossary terms and tags for columns in a pandas DataFrame.

        Args:
            table_name: The name of the table the column belongs to.
            column_stats: The pre-computed statistics for the columns.
            domain: The business domain.

        Returns:
            A BusinessGlossaryOutput model containing glossary terms and tags for each column.
        """
        bg_model = BusinessGlossary(profiling_data=column_stats)
        table_glossary, glossary_df = bg_model(table_name=table_name, domain=domain)
        columns_glossary = []
        for _, row in glossary_df.iterrows():
            columns_glossary.append(
                ColumnGlossary(
                    column_name=row["column_name"],
                    business_glossary=row.get("business_glossary", ""),
                    business_tags=row.get("business_tags", []),
                )
            )
        return BusinessGlossaryOutput(table_name=table_name, table_glossary=table_glossary, columns=columns_glossary)
