# ====================================================================
#  Importing the required python packages
# ====================================================================
import logging
import multiprocessing
import os
import random

from collections import OrderedDict
from datetime import datetime

from functional import pseq
from symspellpy.symspellpy import SymSpell

from intugle.core.settings import settings

from .bag_of_words import (
    extract_bag_of_words_features,
)
from .custom_features import extract_addl_feats

# from .paragraph_vectors import (
#     infer_paragraph_embeddings_features,
# )
from .preprocessing import (
    additional_processing,
    special_token_repl,
)

log = logging.getLogger(__name__)


sym_spell = SymSpell(max_dictionary_edit_distance=settings.DI_CONFIG['THRESHOLD']['SYMSPELL_EDIT_DIST'], prefix_length=settings.DI_CONFIG['THRESHOLD']['PARTITION_SIZE'])


dictionary_path = os.path.join(settings.MODEL_DIR_PATH, "dependant", "datatype_l1_identification", "en-80k.txt")
                                           
# dictionary_path = os.path.join(container_path,model_dep_path,'en-80k.txt')

# # ====================================================================
# # term_index is the column of the term and count_index is the column of the term frequency
# # ====================================================================
sym_spell.load_dictionary(dictionary_path, term_index=settings.DI_CONFIG['THRESHOLD']['SYMSPELL_TERM_INDEX'], count_index=settings.DI_CONFIG['THRESHOLD']['SYMSPELL_COUNT_INDEX'])


# ====================================================================
# CPU Core count for multiprocessing and size of partition size
# ====================================================================
core_count = multiprocessing.cpu_count()  
size = settings.DI_CONFIG['THRESHOLD']['PARTITION_SIZE']

# ====================================================================
# extract_features: 
#     - Extract the required metadata information from values list before feature creation
#     - Clean the table and column name for the embedding creation
#     - Additional preprocessing on the data and passed to the feature creation
#     - Created features one by one from characters, words, and embedding based features
#     - Created the none related features followed by metadata features added
# Parameters: 
#     col_values - List of data for feature creation
# Returns:
#     Returns the features dictionary for the input data
# ====================================================================


def extract_features(col_values: list) -> OrderedDict:
    # Extract features from raw data
    # reuse_model = True
    
    # Extract the table data column from column values
    table_name = col_values[0]
    column_name = col_values[1]
    col_values = col_values[2:]

    # Cleaning the table name for special token replacement and segmenting the compound words
    table_name_clean = special_token_repl(table_name, suffix='_table_name')
    table_name_clean = sym_spell.word_segmentation(table_name_clean).corrected_string

    # Cleaning the column name for special token replacement and segmenting the compound words
    column_name_clean = special_token_repl(column_name, suffix='_column_name')
    column_name_clean = sym_spell.word_segmentation(column_name_clean).corrected_string

    # Number of samples used for feature creation and total samples present in data
    n_samples = settings.DI_CONFIG['THRESHOLD']['DATA_VALUES_LIMIT']
    n_values = len(col_values)

    features = OrderedDict()

    # Additional processing on the col values with nan and lower case converted
    log.info('Custom Preprocessing started:%s', datetime.now())
    cleaned_population_nan = pseq(map(additional_processing, col_values), processes=core_count, partition_size=size)
    cleaned_population_nan = list(cleaned_population_nan)

    log.info('Custom preprocessing completed:%s', datetime.now())
    uniq_cleaned_population = len(set([val.lower() for val in cleaned_population_nan if len(val) > 0]))

    # Based on the number of values, either sample the data or take the entire values
    if n_samples < n_values:
        random.seed(13)
        cleaned_sample_nan = random.sample(cleaned_population_nan, k=n_samples)
    else:
        n_samples = n_values
        cleaned_sample_nan = cleaned_population_nan

    # Additional processing on the col values without nan and lower case converted
    cleaned_sample_wo_nan = [val for val in cleaned_sample_nan if len(val) > 0]
    cleaned_sample_wo_nan_uncased = [val.lower() for val in cleaned_sample_wo_nan]
    # uniq_cleaned_sample = list(set(cleaned_sample_wo_nan))

    # Extracting the bag of character, words, embedding based features along with additional statistical features
    log.info('=' * 100)
    extract_bag_of_words_features(cleaned_sample_nan, cleaned_sample_wo_nan_uncased, features)
    log.info('=' * 100)
    extract_addl_feats(cleaned_sample_nan, features)
    log.info('*' * 100)

    # Creating the additional info for table level data
    features['table_population'] = n_values
    features['table_sample'] = n_samples
    features['uniq_values_population'] = uniq_cleaned_population

    # Additional new features
    features['uniq_samp_pop_ratio'] = features['uniq_values_sample'] / uniq_cleaned_population if uniq_cleaned_population > 0 else 0
    features['samp_pop_ratio'] = n_samples / n_values if n_values > 0 else 0

    lengths = [len(s) for s in cleaned_population_nan]
    n_none = sum(1 for _l in lengths if _l == 0)

    # Creating features releated to 'NA' and 'None'
    features["none-agg-has_population"] = 1 if n_none > 0 else 0
    features["none-agg-percent_population"] = n_none / n_values if n_values > 0 else 1
    features["none-agg-num_population"] = n_none
    features["none-agg-all_population"] = 1 if n_none == n_values else 0

    # new completeness logic
    features['completeness'] = (n_values - n_none) / n_values

    # Adding the metadata specific information of the features
    features['table_name'] = table_name
    features['column_name'] = column_name
    features['table_name_clean'] = table_name_clean
    features['column_name_clean'] = column_name_clean

    log.info('Completed...')
    log.info('#' * 100)
    return features
