# ====================================================================
#  Importing the required python packages
# ====================================================================

import logging
import multiprocessing
import re
import string

import numpy as np
import pandas as pd

# import pyarrow
# ====================================================================
#  Importing the required module packages
# ====================================================================
# from legoai.datatype_identification.bag_of_characters import extract_bag_of_characters_features
# from legoai.datatype_identification.bag_of_words import extract_bag_of_words_features
# from legoai.datatype_identification.word_embeddings import extract_word_embeddings_features
# from legoai.datatype_identification.custom_features import extract_addl_feats
# from legoai.datatype_identification.paragraph_vectors import infer_paragraph_embeddings_features
# from legoai.datatype_identification.global_state import set_first, reset_first
# from legoai.datatype_identification.helpers import literal_eval_as_str, keys_to_csv
# from pyarrow.parquet import ParquetFile
from intugle.core.settings import settings

log = logging.getLogger(__name__)


# Ignore list for the preprocessing values
ignoreList = ['#na', '#n/a', 'na', 'n/a', 'none', 'nan', 'blank', 'blanks', 'nil', 'n.a.', 'n.a',
              '"#na"', '"#n/a"', '"na"', '"n/a"', '"none"', '"nan"', '"blank"', '"blanks"', '"nil"', '"n.a."', '"n.a"',
              "'#na'", "'#n/a'", "'na'", "'n/a'", "'none'", "'nan'", "'blank'", "'blanks'", "'nil'", "'n.a.'", "'n.a'"]

core_count = multiprocessing.cpu_count()  
size = settings.DI_CONFIG['THRESHOLD']['PARTITION_SIZE']


# ====================================================================
# normalise_whitespace: 
#   - Clean whitespace from strings by:
#   - trimming leading and trailing whitespace
#   - normalising all whitespace to spaces
#   - reducing whitespace sequences to a single space
# Parameters: 
#     data - input data
# ====================================================================
def normalise_whitespace(data) -> str:
    if isinstance(data, str):
        return re.sub(r"\s{2,}", " ", data.strip())
    else:
        return data


def normalise_string_whitespace(col_values) -> list:
    # Get the metadata info such as id, dataset, table, column name
    table_name = col_values[0]
    column_name = col_values[1]
    if len(col_values[2:]) > 0:
        normalized_values = list(np.vectorize(normalise_whitespace)(np.array(col_values[2:])))
        # normalized_values = list(pseq(map(additional_processing, col_values[5:]), processes=core_count, partition_size=size))
        # Remove the whitespaces from the data
        # normalized_values = list(map(normalise_whitespace, col_values[5:]))

        # Removing the table and column name from values ## Added to remove features list
        normalized_values = np.vectorize(str)(np.array(normalized_values))

        # Convert to lowercase
        lowercase_values = np.char.lower(normalized_values)

        # # Filter out the unwanted values
        mask = ~np.isin(lowercase_values, [table_name.lower(), column_name.lower()])

        # # Apply the mask
        normalized_values = list(normalized_values[mask])

        # normalized_values = [val for val in normalized_values if
        #                      str(val).lower() not in [dataset_name.lower(), table_name.lower(), column_name.lower()]]

        # Combining the metadata with the normalized values into a list of data
        
    else:
        log.warning(f"[!] Empty column encountered for {table_name} ==> {column_name} ...")
        normalized_values = ['']
        
    normalized_values_upd = [table_name] + [column_name] + normalized_values
    return normalized_values_upd


# ====================================================================
# remove_table_column_name: 
#     -  Remove punctuation characters at start and end of the data
# Parameters: 
#     strs - input string
# ====================================================================
def remove_table_column_name(values: str, table_name: str, column_name: str):
    return [val for val in values if
            str(val).lower() not in [table_name.lower(), column_name.lower()]]


# ====================================================================
# removeASCII: 
#     -  Remove ASCII Characters from the data
# Parameters: 
#     strs - string data for cleaning ascii characters
# ====================================================================
def removeASCII(strs) -> str:
    return ''.join([char for word in str(strs) for char in word if ord(char) < 128])


# ====================================================================
# removePunctuation: 
#     -  Remove punctuation characters at start and end of the data
# Parameters: 
#     strs - input string
# ====================================================================
def removePunctuation(strs) -> str:
    return strs.strip("'").strip('"')


# ====================================================================
# removePunctuation: 
#     - Remove punctuation from the text and check if they are empty
#     - If it contains only punctuations, then return empty else return string 
# Parameters: 
#     strs - input string
# ====================================================================
def removePunctuationText(strs) -> str:
    clean_str = strs.translate(str.maketrans('', '', string.punctuation))
    clean_str = normalise_whitespace(clean_str)
    clean_str = clean_str.strip()
    return '' if len(clean_str) == 0 else strs  # Checks if the string is empty else return string


# ====================================================================
# additional_processing: 
#     - Remove null, nan, none and ignore list elements from data
#     - Remove ASCII Characters and unicode characters
#     - Remove punctuation text and remove punctuation in the start and end text
# Parameters: 
#     value - list of data
# ====================================================================
def additional_processing(value) -> str:

    # Remove the nulls/none and not in ignore list
    if value is None or pd.isnull(value) or str(value).lower() in ignoreList:
        return_val = ''
    else:
        value = str(value).replace('\xa0', ' ').strip()
        return_val = removeASCII(value)

    # Remove punctuation in the start and end text
    return_val = removePunctuationText(return_val)
    
    # Remove punctuation text from text
    return_val = removePunctuation(return_val)
    return return_val


# ====================================================================
# special_token_repl: 
#     -  Remove punctuation characters at start and end of the data
# Parameters: 
#     text - input string
#     suffix - additional text to be added at the end
# ====================================================================
def special_token_repl(text: str, suffix: str) -> str:
    
    # Replace the pattern with empty space and replace multiple space with single space
    replaced_text = text.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
    replaced_text = re.sub(string=replaced_text, pattern=' +', repl=' ')

    # Check if the replaced text is empty then add unknown and suffix word
    if replaced_text == '':
        replaced_text = 'unknown' + suffix

    return replaced_text
