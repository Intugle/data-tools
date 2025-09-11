import pandas as pd

from pydantic import Field

from intugle.common.schema import SchemaBase
from intugle.models.resources.model import Model
from intugle.models.resources.relationship import Relationship
from intugle.models.resources.source import Source


class Manifest(SchemaBase):
    sources: dict[str, Source] = Field(default_factory=dict)
    models: dict[str, Model] = Field(default_factory=dict)
    relationships: dict[str, Relationship] = Field(default_factory=dict)

    @property
    def profiles_df(self) -> pd.DataFrame:
        """Generates a DataFrame with column profiling information."""
        all_profiles = []
        for source in self.sources.values():
            for column in source.table.columns:
                metrics = column.profiling_metrics
                profile_data = {
                    "table_name": source.table.name,
                    "column_name": column.name,
                    "data_type_l1": column.type,
                    "data_type_l2": column.category,
                    "count": metrics.count,
                    "null_count": metrics.null_count,
                    "distinct_count": metrics.distinct_count,
                    "uniqueness": metrics.distinct_count / metrics.count if metrics.count else 0,
                    "completeness": (metrics.count - metrics.null_count) / metrics.count if metrics.count else 0,
                    "sample_values": metrics.sample_data,
                    "business_glossary": column.description,
                    "business_tags": column.tags,
                }
                all_profiles.append(profile_data)
        return pd.DataFrame(all_profiles)

    @property
    def links_df(self) -> pd.DataFrame:
        """Generates a DataFrame with link prediction information."""
        link_data = []
        for relationship in self.relationships.values():
            left_table_name = relationship.source.table
            left_column_name = relationship.source.column
            right_table_name = relationship.target.table
            right_column_name = relationship.target.column

            left_source = self.sources.get(left_table_name)
            right_source = self.sources.get(right_table_name)

            if left_source and right_source:
                left_column = next((c for c in left_source.table.columns if c.name == left_column_name), None)
                right_column = next((c for c in right_source.table.columns if c.name == right_column_name), None)

                if left_column and right_column:
                    left_metrics = left_column.profiling_metrics
                    right_metrics = right_column.profiling_metrics
                    link_data.append(
                        {
                            "left_table": left_table_name,
                            "left_column": left_column_name,
                            "left_data_type_l1": left_column.type,
                            "left_data_type_l2": left_column.category,
                            "left_count": left_metrics.count,
                            "left_uniqueness": left_metrics.distinct_count / left_metrics.count
                            if left_metrics.count
                            else 0,
                            "left_completeness": (left_metrics.count - left_metrics.null_count) / left_metrics.count
                            if left_metrics.count
                            else 0,
                            "left_sample_values": left_metrics.sample_data,
                            "right_table": right_table_name,
                            "right_column": right_column_name,
                            "right_data_type_l1": right_column.type,
                            "right_data_type_l2": right_column.category,
                            "right_count": right_metrics.count,
                            "right_uniqueness": right_metrics.distinct_count / right_metrics.count
                            if right_metrics.count
                            else 0,
                            "right_completeness": (right_metrics.count - right_metrics.null_count)
                            / right_metrics.count
                            if right_metrics.count
                            else 0,
                            "right_sample_values": right_metrics.sample_data,
                        }
                    )
        return pd.DataFrame(link_data)

    @property
    def business_glossary_df(self) -> pd.DataFrame:
        """Generates a DataFrame with business glossary information."""
        glossary_data = []
        for source in self.sources.values():
            for column in source.table.columns:
                glossary_data.append(
                    {
                        "table_name": source.table.name,
                        "column_name": column.name,
                        "business_glossary": column.description,
                        "business_tags": column.tags,
                    }
                )
        return pd.DataFrame(glossary_data)
