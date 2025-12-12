import os

from typing import Dict

import pandas as pd


class ParquetTarget:
    """
    Writes data to Parquet files.
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def write(self, tables: Dict[str, pd.DataFrame]) -> None:
        """
        Writes a dictionary of DataFrames to Parquet files in the output directory.
        
        Args:
            tables: A dictionary where keys are table names and values are DataFrames.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        for table_name, df in tables.items():
            if not df.empty:
                file_path = os.path.join(self.output_dir, f"{table_name}.parquet")
                df.to_parquet(file_path, index=False)
