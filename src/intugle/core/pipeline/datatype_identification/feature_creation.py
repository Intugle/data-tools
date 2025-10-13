import gc
import logging
import multiprocessing

from datetime import datetime
from time import time
from typing import Optional

import pandas as pd

from functional import pseq
from tqdm.auto import tqdm

from intugle.core.settings import settings

from .functional import extract_features
from .preprocessing import (
    normalise_string_whitespace,
    remove_table_column_name,
)

log = logging.getLogger(__name__)


tqdm.pandas()
size = settings.DI_CONFIG["THRESHOLD"]["PARTITION_SIZE"]
core_count = multiprocessing.cpu_count()


class DIFeatureCreation:
    
    def __init__(self,):
        ...

    def __convert_logical_parquet__(self, parquet_df: pd.DataFrame) -> pd.DataFrame:

        parquet_df['clean_values'] = parquet_df.apply(lambda x: remove_table_column_name(x['values'], x['table_name'], x['column_name']), axis=1)

        # Converting the metadata into string format
        parquet_df['table_name'] = parquet_df['table_name'].astype(str)
        parquet_df['column_name'] = parquet_df['column_name'].astype(str)

        return parquet_df
    
    def __extract__(self, parquet_values: list, pool: Optional[multiprocessing.Pool] = None) -> pd.DataFrame:
        if pool:
            normalized_list = pool.map(normalise_string_whitespace, parquet_values)
            features_dict = pool.map(extract_features, normalized_list)
        else:
            normalized_list = pseq(map(normalise_string_whitespace, parquet_values), processes=core_count, partition_size=size)
            features_dict = pseq(map(extract_features, normalized_list), processes=core_count, partition_size=size)

        return pd.DataFrame.from_dict(features_dict)
        
    def __call__(self, sample_values_df: pd.DataFrame) -> pd.DataFrame:

        with multiprocessing.Pool(multiprocessing.cpu_count(),) as pool:
            
            parquet_df = sample_values_df

            log.info(f"[*]Total Columns Present in the entire repo: {parquet_df.shape[0]}")
            start_ft = datetime.now()
            
            log.info(f"[*] Feature Creation Started at: {start_ft}")
            
            parquet_df = self.__convert_logical_parquet__(parquet_df)
            
            # Converting data values into a single list format
            table_name = parquet_df['table_name'].values.tolist()
            column_name = parquet_df['column_name'].values.tolist()
            data_values = parquet_df['clean_values'].values.tolist()

            # Combining the metadata + values data

            # features_df = pd.DataFrame()
            parquet_values = [[table_name[val]] + [column_name[val]] + list(data_values[val]) for val in range(len(parquet_df))]
            
            del parquet_df
            gc.collect()
            
            start = time()
            
            features_df = self.__extract__(parquet_values=parquet_values, pool=pool if settings.DI_CONFIG["FEATURES"]["PARALLEL"] else None)

            end = time()

            log.info(f"[**] FEATS COMPUTATION <dtype_features> ==> {round((end - start) / 60, 3)} minutes")
            assert features_df.shape[0] != 0, "Features dataframe is empty"
            # Get the total number of null features and replace them with 0
            # Get the feature execution stats
            features_df['start_time'] = start_ft
            features_df['end_time'] = datetime.now()
            features_df['execution_time'] = datetime.now() - start_ft
        
        # log.info(f"Feature Creation Finished. Processed {len_repo} rows in {round((datetime.now() - start_ft)/60,3)} minutes")
        
        return features_df        