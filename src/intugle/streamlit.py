import os
from typing import TYPE_CHECKING

import pandas as pd

from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.libs.smart_query_generator import SmartQueryGenerator
from intugle.libs.smart_query_generator.models.models import ETLModel, FieldDetailsModel, LinkModel
from intugle.libs.smart_query_generator.utils.join import Join
from intugle.parser.manifest import ManifestLoader

if TYPE_CHECKING:
    from intugle.models.resources.model import Column


class StreamlitApp:

    def __init__(self, project_base: str = settings.PROJECT_BASE):
        self.manifest_loader = ManifestLoader(project_base)
        self.manifest_loader.load()
        self.manifest = self.manifest_loader.manifest

        self.project_base = project_base

        self.field_details = self.get_all_field_details()

        # get the links from the manifest
        self.links = self.get_links()

        selected_fields = set(self.field_details.keys())
        self.join = Join(self.links, selected_fields)
        
        self.datasets: dict[str, DataSet] = {}

        self.load_all()

    def load_all(self):
        sources = self.manifest.sources
        for source in sources.values():
            table_name = source.table.name
            details = source.table.details
            dataset = DataSet(data=details, name=table_name)
            self.datasets[table_name] = dataset

    def get_all_field_details(self) -> dict[str, FieldDetailsModel]:
        """Fetches all field details from the manifest."""

        # get sources from the manifest
        sources = self.manifest.sources

        field_details: dict[str, FieldDetailsModel] = {}

        # iterate through each source and get the field details (all fields / columns)
        for source in sources.values():
            for column in source.table.columns:
                field_detail: FieldDetailsModel = FieldDetailsModel(
                    id=f"{source.table.name}.{column.name}",
                    name=column.name,
                    datatype_l1=column.type,
                    datatype_l2=column.category,
                    sql_code=f"\"{source.table.name}\".\"{column.name}\"",
                    is_pii=False,
                    asset_id=source.table.name,
                    asset_name=source.table.name,
                    asset_details={},
                    connection_id=source.schema,
                    connection_source_name="postgresql",
                    connection_credentials={},
                )
                field_details[field_detail.id] = field_detail

        return field_details

    def get_links(self) -> list[LinkModel]:
        """Fetches the links from the manifest."""

        # get relationships from the manifest
        relationships = self.manifest.relationships
        links: list[LinkModel] = []

        # iterate through each relationship and create a LinkModel
        for relationship in relationships.values():
            links.append(relationship.link)
        return links

    def export_analysis_to_csv(self):
        """Exports the analysis results to CSV files."""
        # 1. Column Profiles CSV
        all_profiles = []
        for source in self.manifest.sources.values():
            for column in source.table.columns:
                profile_data = {
                    "table_name": source.table.name,
                    "column_name": column.name,
                    "data_type_l1": column.type,
                    "data_type_l2": column.category,
                    "count": column.profiling_metrics.count,
                    "uniqueness": column.profiling_metrics.distinct_count / column.profiling_metrics.count
                    if column.profiling_metrics.count
                    else 0,
                    "completeness": (column.profiling_metrics.count - column.profiling_metrics.null_count)
                    / column.profiling_metrics.count
                    if column.profiling_metrics.count
                    else 0,
                    "sample_values": column.profiling_metrics.sample_data,
                }
                all_profiles.append(profile_data)
        column_profiles_df = pd.DataFrame(all_profiles)
        column_profiles_df.to_csv(os.path.join(self.project_base, "column_profiles.csv"), index=False)

        # 2. Link Predictions CSV
        link_data = []
        for relationship in self.manifest.relationships.values():
            left_table_name = relationship.source.table
            left_column_name = relationship.source.column
            right_table_name = relationship.target.table
            right_column_name = relationship.target.column

            left_source = self.manifest.sources.get(left_table_name)
            right_source = self.manifest.sources.get(right_table_name)

            if left_source and right_source:
                left_column_data = next(
                    (col for col in left_source.table.columns if col.name == left_column_name), None
                )
                right_column_data = next(
                    (col for col in right_source.table.columns if col.name == right_column_name), None
                )

                if left_column_data and right_column_data:
                    link_data.append(
                        {
                            "left_table": left_table_name,
                            "left_column": left_column_name,
                            "left_data_type_l1": left_column_data.type,
                            "left_data_type_l2": left_column_data.category,
                            "left_count": left_column_data.profiling_metrics.count,
                            "left_uniqueness": left_column_data.profiling_metrics.distinct_count
                            / left_column_data.profiling_metrics.count
                            if left_column_data.profiling_metrics.count
                            else 0,
                            "left_completeness": (
                                left_column_data.profiling_metrics.count - left_column_data.profiling_metrics.null_count
                            )
                            / left_column_data.profiling_metrics.count
                            if left_column_data.profiling_metrics.count
                            else 0,
                            "left_sample_values": left_column_data.profiling_metrics.sample_data,
                            "right_table": right_table_name,
                            "right_column": right_column_name,
                            "right_data_type_l1": right_column_data.type,
                            "right_data_type_l2": right_column_data.category,
                            "right_count": right_column_data.profiling_metrics.count,
                            "right_uniqueness": right_column_data.profiling_metrics.distinct_count
                            / right_column_data.profiling_metrics.count
                            if right_column_data.profiling_metrics.count
                            else 0,
                            "right_completeness": (
                                right_column_data.profiling_metrics.count
                                - right_column_data.profiling_metrics.null_count
                            )
                            / right_column_data.profiling_metrics.count
                            if right_column_data.profiling_metrics.count
                            else 0,
                            "right_sample_values": right_column_data.profiling_metrics.sample_data,
                        }
                    )
        link_predictions_df = pd.DataFrame(link_data)
        link_predictions_df.to_csv(os.path.join(self.project_base, "link_predictions.csv"), index=False)

        # 3. Business Glossary CSV
        glossary_data = []
        for source in self.manifest.sources.values():
            for column in source.table.columns:
                glossary_data.append(
                    {
                        "table_name": source.table.name,
                        "column_name": column.name,
                        "business_glossary": column.description,
                        "business_tags": column.tags,
                    }
                )
        glossary_df = pd.DataFrame(glossary_data)
        glossary_df.to_csv(os.path.join(self.project_base, "business_glossary.csv"), index=False)

    
