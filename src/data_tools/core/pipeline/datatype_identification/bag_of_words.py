# ====================================================================
#  Importing the required python packages
# ====================================================================

import logging
import math
import re
import statistics as statistics

from collections import OrderedDict
from datetime import datetime

import nltk
import numpy as np

from intugle.core.settings import settings
from intugle.core.utilities.processing import compute_stats

from .global_state import is_first

log = logging.getLogger(__name__)


# ====================================================================
# count_pattern_in_cells: 
#  - Get the length of matching patterns present in the string for each values
# Parameters: 
#     values - list of data values
#     pat - regex pattern for counting within the cells
# Returns:
#    List of length of matching patterns present in string
# ====================================================================
def count_pattern_in_cells(values: list, pat: str) -> list:
    return [len(re.findall(pat, s)) for s in values]


# ====================================================================
# count_pattern_in_cells_with_non_zero_count: 
#  - Get the length of matching patterns present in the string for each values
#  - Count the number of elements with pattern matched in each text
# Parameters: 
#     values - list of data values
#     pat - regex pattern for counting within the cells
# Returns:
#    Tuple of total number of elements with matched pattern, and total cell counts
# ====================================================================
def count_pattern_in_cells_with_non_zero_count(values: list, pat: str):    
    cell_counts = [len(re.findall(pat, s)) for s in values]
    return sum(1 for c in cell_counts if c > 0), cell_counts


# ====================================================================
# Various patterns for number, text, word and special characters 
# ====================================================================
NUMBER_PATTERN = re.compile(settings.DI_CONFIG['PREPROCESS_CONSTANT']['NUMBER_PATTERN'])
TEXT_PATTERN = re.compile(settings.DI_CONFIG['PREPROCESS_CONSTANT']['TEXT_PATTERN'])
WORD_PATTERN = re.compile(settings.DI_CONFIG['PREPROCESS_CONSTANT']['WORD_PATTERN'])
SPECIAL_CHARACTERS_PATTERN = re.compile(settings.DI_CONFIG['PREPROCESS_CONSTANT']['SPECIAL_CHAR_PATTERN'])

# ====================================================================
# extract_bag_of_words_features: 
#  - Get the length of values for feature creation
#  - Calculate the Entropy of column
#  - Fraction of cells with unique content, numeric content, alpha and special character
#  - Ratio calculation for numeric to char to alphanumeric and others
#  - Get the none related features for sample data (flag, percent, count)    
# Parameters: 
#     col_values - list of data values
#     col_values_wo_nan_uncased - list of data values without nan and lower cased
#     features - features dict with features for each values
# Returns:
#    Ordered dictionary holding bag of words features
# ====================================================================


def extract_bag_of_words_features(col_values: list, col_values_wo_nan_uncased: list, features: OrderedDict):
    
    # Get the length of values for feature creation
    start_time = datetime.now()
    n_val = len(col_values)

    log.info('Bag of words started:%s', start_time)
    log.info('Bag of words col entropy started:%s', datetime.now())

    # Calculate the Entropy of column
    freq_dist = nltk.FreqDist(col_values_wo_nan_uncased)
    probs = [freq_dist.freq(_l) for _l in freq_dist]
    features["col_entropy"] = -sum(p * math.log(p, 2) for p in probs)

    log.info('Bag of words frac unique started:%s', datetime.now())

    # Fraction of cells with unique content
    num_unique = len(set(col_values_wo_nan_uncased))

    # Setting the default values to 0 if no data is present
    if len(col_values_wo_nan_uncased) == 0:
        features["frac_unique_sample"] = 0
        features['uniq_values_sample'] = 0

    else:
        features["frac_unique_sample"] = num_unique / len(col_values_wo_nan_uncased)
        features['uniq_values_sample'] = len(set(col_values_wo_nan_uncased))

    # Fraction of cells with numeric content -> frac text cells doesn't add information
    numeric_cell_nz_count, numeric_char_counts = count_pattern_in_cells_with_non_zero_count(
        col_values, NUMBER_PATTERN
    )
    text_cell_nz_count, text_char_counts = count_pattern_in_cells_with_non_zero_count(
        col_values, TEXT_PATTERN
    )

    # Average + std number of special characters in each cell
    spec_char_counts = count_pattern_in_cells(col_values, SPECIAL_CHARACTERS_PATTERN)

    # Alphanumeric cell count present in each values
    alphanum_cell_counts = [len(col_values[idx]) if (
            numeric_char_counts[idx] > 0 and (spec_char_counts[idx] > 0 or text_char_counts[idx] > 0)) else 0 for
                            idx in range(len(col_values))]
    alphanum_cell_nz_count, alphanum_char_counts = sum(1 for c in alphanum_cell_counts if c > 0), alphanum_cell_counts

    # Ratio calculation for numeric to char to alphanumeric
    features["numeric_alpha_ratio"] = np.mean(
        [numeric_char_counts[idx] / text_char_counts[idx] if text_char_counts[idx] > 0 else 0 for idx in
         range(len(col_values))])
    features["numeric_char_ratio"] = np.mean(
        [numeric_char_counts[idx] / spec_char_counts[idx] if spec_char_counts[idx] > 0 else 0 for idx in
         range(len(col_values))])
    features["char_alpha_ratio"] = np.mean(
        [spec_char_counts[idx] / text_char_counts[idx] if text_char_counts[idx] > 0 else 0 for idx in
         range(len(col_values))])

    # Count of numeric, char, alphanumeric values
    features["numeric_cell_nz_count"] = numeric_cell_nz_count
    features["text_cell_nz_count"] = text_cell_nz_count
    features["alphanum_cell_nz_count"] = alphanum_cell_nz_count

    # Ratio calculation for numeric to char to alphanumeric values
    features["frac_numcells"] = numeric_cell_nz_count / n_val if n_val > 0 else 0
    features["frac_textcells"] = text_cell_nz_count / n_val if n_val > 0 else 0
    features["frac_alphanumcells"] = alphanum_cell_nz_count / n_val if n_val > 0 else 0

    # Presence flag for numeric, char, alphanumeric values
    features["flag_numcells"] = np.mean([1 if val > 0 else 0 for val in numeric_char_counts])
    features["flag_textcells"] = np.mean([1 if val > 0 else 0 for val in text_char_counts])
    features["flag_speccells"] = np.mean([1 if val > 0 else 0 for val in spec_char_counts])

#     log.info('Bag of words avg,std features started:%s', datetime.now())

    # Average + std number of numeric tokens in cells
    features["avg_num_cells"] = np.mean(numeric_char_counts) if n_val > 0 else 0
    features["std_num_cells"] = np.std(numeric_char_counts) if n_val > 0 else 0

    # Average + std number of textual tokens in cells
    features["avg_text_cells"] = np.mean(text_char_counts) if n_val > 0 else 0
    features["std_text_cells"] = np.std(text_char_counts) if n_val > 0 else 0

    # Average + std number of alphanum tokens in cells
    features["avg_alphanum_cells"] = np.mean(alphanum_char_counts) if n_val > 0 else 0
    features["std_alphanum_cells"] = np.std(alphanum_char_counts) if n_val > 0 else 0

    features["avg_spec_cells"] = np.mean(spec_char_counts) if n_val > 0 else 0
    features["std_spec_cells"] = np.std(spec_char_counts) if n_val > 0 else 0

    # Average number of words in each cell
    word_counts = count_pattern_in_cells(col_values, WORD_PATTERN)

    # Average + std number of word count in cells
    features["avg_word_cells"] = np.mean(word_counts) if n_val > 0 else 0
    features["std_word_cells"] = np.std(word_counts) if n_val > 0 else 0

    # length of each element in cells
    lengths = [len(s) for s in col_values]
    n_none = sum(1 for _l in lengths if _l == 0)

    has_any = any(lengths)

    log.info('Bag of words statistical features started:%s', datetime.now())

    if has_any:
        _any = 1
        _all = 1 if all(lengths) else 0
        _mean, _variance, _skew, _kurtosis, _min, _max, _sum = compute_stats(lengths)
        _median = statistics.median(lengths)

        if is_first():
            # the first output needs fully expanded keys (to drive CSV header)
            features["length-agg-any"] = _any
            features["length-agg-all"] = _all
            features["length-agg-mean"] = _mean
            features["length-agg-var"] = _variance
            features["length-agg-min"] = _min
            features["length-agg-max"] = _max
            features["length-agg-median"] = _median
            features["length-agg-sum"] = _sum
            features["length-agg-kurtosis"] = _kurtosis
            features["length-agg-skewness"] = _skew
        else:
            # subsequent lines only care about values, so we can pre-render a block of CSV. This
            # cuts overhead of storing granular values in the features dictionary
            features[
                "length-pre-rendered"
            ] = f"{_any},{_all},{_mean},{_variance},{_min},{_max},{_median},{_sum},{_kurtosis},{_skew}"
    else:
        if is_first():
            features["length-agg-any"] = 0
            features["length-agg-all"] = 0
            features["length-agg-mean"] = 0
            features["length-agg-var"] = 0
            features["length-agg-min"] = 0
            features["length-agg-max"] = 0
            features["length-agg-median"] = 0
            features["length-agg-sum"] = 0
            features["length-agg-kurtosis"] = -3
            features["length-agg-skewness"] = 0
        else:
            # assign pre-rendered defaults
            features["length-pre-rendered"] = "0,0,0,0,0,0,0,0,-3,0"

    log.info('Bag of words none features started:%s', datetime.now())

    # Get the none related features for sample data (flag, percent, count)    
    features["none-agg-has_sample"] = 1 if n_none > 0 else 0
    features["none-agg-percent_sample"] = n_none / n_val if n_val > 0 else 1
    features["none-agg-num_sample"] = n_none
    features["none-agg-all_sample"] = 1 if n_none == n_val else 0

    end_time = datetime.now()
    log.info('Bag of words completed:%s', end_time)
    log.info('Total time taken for bag of words:%s', end_time - start_time)
