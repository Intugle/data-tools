# ====================================================================
#  Importing the required python packages
# ====================================================================

import itertools
import logging
import math as math
import os
import statistics as statistics

from collections import OrderedDict
from datetime import datetime

import numpy as np

from data_tools.core.settings import settings

from .global_state import is_first
from .stats_helper import mode

log = logging.getLogger(__name__)


# ====================================================================
# initialise_word_embeddings: 
#     - Read the Glove Word Embeddings text file
#     - Split the words and the respective embeddings and store in a dictionary
# Parameters: 
#     path - Glove model file path
# ====================================================================

# Dictionary to store word level embeddings
word_to_embedding = {}


def initialise_word_embeddings(path: str):
    start = datetime.now()

    global word_to_embedding
    
    # dont initialze if already initialized
    if len(word_to_embedding) != 0:
        return 
    
    log.info("[*] Initialising word embeddings")
    
    # Reading the glove model path 
    word_vectors_f = open(
        os.path.join(settings.MODEL_DIR_PATH, "dependant",
                     "datatype_l1_identification",
                     "glove.6B.50d.txt"), encoding="utf-8")

    # Split the word and store the respective vectors into float format 
    for w in word_vectors_f:
        term, vector = w.strip().split(' ', 1)
        vector = list(map(float, vector.split(' ')))
        
        # Store the term/word as key and value or embeddings as values
        word_to_embedding[term] = vector

    end = datetime.now()
    x = end - start

    word_vectors_f.close()

    log.info(f'[*] Initialise Word Embeddings process took {x} seconds.')

# ====================================================================
# transpose: Transpose the given the input array
# Parameters: 
#     a - input array
# ====================================================================


ZEROS = [0] * 50
REPL_STR = 0
# nans for mean, median, stdev and mode for each embedding
NANS = ','.join(map(str, [REPL_STR] * 50 * 4))


def transpose(a):
    # transpose array:
    #   >>> theArray = [['a','b','c'],['d','e','f'],['g','h','i']]
    #   >>> [*zip(*theArray)]
    #   [('a', 'd', 'g'), ('b', 'e', 'h'), ('c', 'f', 'i')]
    #
    #   https://stackoverflow.com/questions/4937491/matrix-transpose-in-python
    return [*zip(*a)]

# ====================================================================
# extract_word_embeddings_features: 
#  - Load the pretrained Glove Word embeddings for vector creation
#  - Iterate through each elements in the list of input col values
#  - Split the each values into multiple words and get the embeddings for each word
#  - Calculate the mean of words in each element to aggregate at an element level
#  - Calculate the various statistical level of the value embeddings such as avg, std, mode, median
# Parameters: 
#     col_values - collection of columns stored in a dataframe column 'values'
#     features - Features dictionary 
#     prefix - type of embedding for table, column or value level
# Returns: 
#     ordered dictionary holding word embedding features
# ====================================================================


def extract_word_embeddings_features(col_values: list, features: OrderedDict, prefix: str):
    start_time = datetime.now()
    log.info('[*] Word embeddings feature started:%s', start_time)

    # Glove vector Embedding size
    num_embeddings = settings.DI_CONFIG['THRESHOLD']['GLOVE_DIM_SIZE']

    embeddings = []

    global word_to_embedding
    
    # If word embedding is not present, then initialize the pretrained word embedding
    if not word_to_embedding:
        par_vec_path = os.path.join(settings.MODEL_DIR_PATH, "dependant", "datatype_l1_identification")
        initialise_word_embeddings(par_vec_path)

    # Iterate through each column values and get the word level embeddings
    for col_value in map(str.lower, col_values):
        if col_value in word_to_embedding:
            embeddings.append(word_to_embedding.get(col_value))
        else:
            embeddings_to_all_words = [word_to_embedding.get(w) for w in col_value.split(' ') if w in word_to_embedding]

            n = len(embeddings_to_all_words)

            # Get the word level embeddings and aggregate it to mean/average of word level embeddings
            if n == 1:
                embeddings.append(embeddings_to_all_words[0])
            elif n > 1:
                mean_of_word_embeddings = np.mean(embeddings_to_all_words, dtype=float, axis=0)
                embeddings.append(mean_of_word_embeddings)

    n_rows = len(embeddings)
    log.info('[*] Word embeddings statistical aggregation started:%s', datetime.now())
    
    # If the word are not present in the Glove vocabulary, the give the default value as 0
    if n_rows == 0:
        if is_first():
            # the first output needs fully expanded keys (to drive CSV header)
            # need to maintain same insertion order as the other case, hence running for loop per feature
            for i in range(num_embeddings):
                features[prefix + '_word_embedding_avg_' + str(i)] = REPL_STR
            for i in range(num_embeddings):
                features[prefix + '_word_embedding_std_' + str(i)] = REPL_STR
            for i in range(num_embeddings):
                features[prefix + '_word_embedding_med_' + str(i)] = REPL_STR
            for i in range(num_embeddings):
                features[prefix + '_word_embedding_mode_' + str(i)] = REPL_STR
        else:
            # subsequent lines only care about values, so we can pre-render a block of CSV. This
            # cuts overhead of storing granular values in the features dictionary
            features[prefix + '_word_embedding-pre-rendered'] = NANS

        features[prefix + '_word_embedding_feature'] = 0

    else:
        if n_rows > 1:
            mean_embeddings = []
            std_embeddings = []
            med_embeddings = []
            mode_embeddings = []

            # transpose array (if using numpy, stats would operate on axis=0):
            for axis0 in transpose(embeddings):
                # mode requires sorted list, and Python's sort is super quick on presorted arrays. The subsequent
                # median calc also calls sorted(), so this helps there, too.
                #
                # Re: sorting in Python
                #   https://stackoverflow.com/questions/1436962/python-sort-method-on-list-vs-builtin-sorted-function
                axis0 = sorted(axis0)

                _mean = sum(axis0) / n_rows

                mean_embeddings.append(_mean)

                _variance = sum((x - _mean) ** 2 for x in axis0) / n_rows
                std_embeddings.append(math.sqrt(_variance))

                med_embeddings.append(statistics.median(axis0))

                mode_embeddings.append(mode(axis0, True))
        # n_rows == 1
        else:
            # if only one dimension, then mean, median and mode are equivalent to the embedding data
            mean_embeddings = med_embeddings = mode_embeddings = embeddings[0]
            std_embeddings = ZEROS

        if is_first():
            # the first output needs fully expanded keys (to drive CSV header)
            for i, e in enumerate(mean_embeddings):
                features[prefix + '_word_embedding_avg_' + str(i)] = e
            for i, e in enumerate(std_embeddings):
                features[prefix + '_word_embedding_std_' + str(i)] = e
            for i, e in enumerate(med_embeddings):
                features[prefix + '_word_embedding_med_' + str(i)] = e
            for i, e in enumerate(mode_embeddings):
                features[prefix + '_word_embedding_mode_' + str(i)] = e
        else:
            # subsequent lines only care about values, so we can pre-render a block of CSV. This
            # cuts overhead of storing granular values in the features dictionary
            features['word_embedding-pre-rendered'] = \
                ','.join(map(lambda x: '%g' % x,
                             itertools.chain(mean_embeddings, std_embeddings, med_embeddings, mode_embeddings)))

        features[prefix + '_word_embedding_feature'] = 1

    log.info('[*] Word embeddings statistical aggregation completed:%s', datetime.now())

    end_time = datetime.now()
    log.info('[*] Word embeddings feature completed:%s', end_time)
    log.info('[*] Total time taken for word embeddings features:%s', end_time - start_time)
