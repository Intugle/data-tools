import os

import pandas as pd

from intugle.parser.manifest import Manifest


class CSVExporter:
    def __init__(self, manifest: Manifest, project_base: str):
        self.manifest = manifest
        self.project_base = project_base

    def _export_column_profiles(self, file_path: str):
        df = self.manifest.profiles_df
        profile_columns_to_keep = [
            col for col in df.columns if col not in ["business_glossary", "business_tags"]
        ]
        df[profile_columns_to_keep].to_csv(file_path, index=False)

    def _export_link_predictions(self, file_path: str):
        df = self.manifest.links_df
        df.to_csv(file_path, index=False)

    def _export_business_glossary(self, file_path: str):
        df = self.manifest.business_glossary_df
        df.to_csv(file_path, index=False)

    def export_all(
        self,
        column_profiles_file="column_profiles.csv",
        link_predictions_file="link_predictions.csv",
        business_glossary_file="business_glossary.csv",
    ):
        self._export_column_profiles(os.path.join(self.project_base, column_profiles_file))
        self._export_link_predictions(os.path.join(self.project_base, link_predictions_file))
        self._export_business_glossary(os.path.join(self.project_base, business_glossary_file))
