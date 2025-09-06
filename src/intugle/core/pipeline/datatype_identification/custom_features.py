# ====================================================================
#  Importing the required python packages
# ====================================================================

import logging
import multiprocessing
import re

from collections import Counter, OrderedDict
from datetime import datetime

import numpy as np
import pandas as pd

from functional import pseq
from nltk.corpus import words
from trieregex import TrieRegEx as TRE

from intugle.core.settings import settings
from intugle.core.utilities.processing import compute_stats, to_high_precision_array

from .initialize import di_initalizer

log = logging.getLogger(__name__)


try:
    x = words.words()
except Exception:
    di_initalizer()

words_list = []
for value in words.words():
    if len(value) > settings.DI_CONFIG["THRESHOLD"]["CORPUS_WORD_LIMIT"]:
        words_list.append(value.lower())

# ### TRIE REGEX for the words list
tre = TRE()
tre = TRE(*words_list)


# Get the core count and partition size for multiprocessing
core_count = multiprocessing.cpu_count()  # 1
size = settings.DI_CONFIG["THRESHOLD"]["PARTITION_SIZE"]

# Get the minimum and maximum range for the date extraction
minRange = settings.DI_CONFIG["THRESHOLD"]["DATE_MIN_YEAR"]
maxRange = settings.DI_CONFIG["THRESHOLD"]["DATE_MAX_YEAR"]


# ====================================================================
# checkInt:
#  - Check if the data is of Integer type or not
#  - If integer then return 1 else 0
# Parameters:
#     strs - input data (check if the data is integer or not)
# ====================================================================
def checkInt(strs) -> int:
    # If integer type then return 1 else return 0
    if isinstance(strs.replace(",", ""), int):
        return 1
    elif isinstance(
        strs.replace(",", ""), float
    ):  # If the data is matching for float return 0
        return 0
    else:
        try:
            int(strs.replace(",", ""))
            return 1
        except Exception:
            return 0


# ====================================================================
# checkFloat:
#  - Check if the data is of Float type or not
#  - If float then return 1 else 0
# Parameters:
#     strs - input data (check if the data is float or not)
# ====================================================================
def checkFloat(strs) -> int:
    # If Float type then return else return 0
    if isinstance(strs, float):
        return 1
    else:
        try:
            if checkInt(
                strs.replace(",", "")
            ):  # If the data is matching for Integer return 0
                return 0
            strs = float(strs.replace(",", ""))
            if strs != np.inf:  # If the data is matching for Infinity return 1
                return 1
            else:
                return 0
        except Exception:
            return 0


# ====================================================================
# alphaAndNumericMatch:
#  - Calculate the ratio of alpha to numeric ratio
#  - If the data is only alpha then returns alpha
#  - If the data is only numeric then return numeric
#  - If the data contains both alpha and numeric or special character then return alphanumeric
# Parameters:
#     value - input data
# ====================================================================


def otherSpecialCharacterCheck(value: str) -> int:
    """
    Handling special strings like 9.8.1 , 10.0.0 as alphanumperic
    Args:
        value (str): _description_

    Returns:
        int: _description_
    """
    # float pattern to also match edge floats like '9.' or '.5'
    float_pattern = re.compile(settings.DI_CONFIG["PREPROCESS_CONSTANT"]["FLOAT_PATTERN"])

    # Remove all float-like substrings
    text_without_floats = float_pattern.sub("", value)

    # Count remaining special characters
    special_chars = re.findall(
        pattern=settings.DI_CONFIG["PREPROCESS_CONSTANT"]["SPECIAL_CHARACTER_PATTERN_WITH_DOT"],
        string=text_without_floats,
    )
    return len(special_chars)


def alphaAndNumericMatch(value) -> str:
    # Converts the values into string type
    value = str(value)

    # Get the length of
    charCount = len(
        re.findall(
            string=value, pattern=settings.DI_CONFIG["PREPROCESS_CONSTANT"]["TEXT_PATTERN"]
        )
    )
    numCount = len(
        re.findall(
            string=value, pattern=settings.DI_CONFIG["PREPROCESS_CONSTANT"]["NUMBER_PATTERN"]
        )
    )
    specialCharCount = len(
        re.findall(
            string=value,
            pattern=settings.DI_CONFIG["PREPROCESS_CONSTANT"]["SPECIAL_CHAR_PATTERN"],
        )
    )
    otherspecialCharCount = otherSpecialCharacterCheck(value)

    # Based on the occurence of the characters and number return the respective types
    if (charCount > 0 or specialCharCount or otherspecialCharCount) and numCount > 0:
        return "alphanumeric"
    elif numCount > 0:
        return "numeric"
    elif charCount > 0:
        return "alpha"
    else:
        return "others"


# ====================================================================
# intTypeData:
#  - Iterate through each element and check if they are integer type
#  - Get the total length of characters in the integer data
#  - If the length of int type is 0, then return default values else compute the statistics
# Parameters:
#     col_values - list of input data
# ====================================================================
def intTypeData(col_values):
    # Iterate through each element and check if they are integer type
    int_type_data = [int(element) for element in col_values if checkInt(element)]
    int_type_ratio = len(int_type_data) / len(col_values)
    _median = np.median(int_type_data)

    # Get the total length of characters in the integer data
    try:
        mean_before_int = np.mean([len(str(val)) for val in int_type_data])
    except Exception:
        mean_before_int = 0

    # If the length of int type is 0, then return default values else compute the statistics
    if len(int_type_data) > 0:
        _mean, _variance, _skew, _kurtosis, _min, _max, _sum = compute_stats(
            int_type_data
        )
        return (
            int_type_data,
            int_type_ratio,
            _mean,
            _median,
            _variance,
            _skew,
            _kurtosis,
            _min,
            _max,
            _sum,
            mean_before_int,
        )
    else:
        return int_type_data, int_type_ratio, 0, 0, 0, 0, -3, 0, 0, 0, mean_before_int


# ====================================================================
# floatTypeData:
#  - Iterate through each element and check if they are float type
#  - Get the total length of characters, before and after decimal point in the float data
#  - Check if the max value is 0, then set the flag = 1 else 0
#  - If the length of float type is 0, then return default values else compute the statistics
# Parameters:
#     col_values - list of input data
# ====================================================================
def floatTypeData(col_values):
    # Iterate through each element and check if they are float type
    float_type_data = [float(element) for element in col_values if checkFloat(element)]
    float_type_ratio = len(float_type_data) / len(col_values)
    _median = np.median(float_type_data)

    # Get the total length of characters, before and after decimal point in the float data
    try:
        mean_before_float = np.mean(
            [
                len(str(float(val)).split(".")[0])
                for val in float_type_data
                if pd.notnull(val)
            ]
        )
        mean_after_float = np.mean(
            [
                len(str(float(val)).split(".")[1])
                for val in float_type_data
                if len(str(float(val)).split(".")) > 1 and pd.notnull(val)
            ]
        )
        max_after_float = max(
            [
                int(str(float(val)).split(".")[1])
                for val in float_type_data
                if len(str(float(val)).split(".")) > 1 and pd.notnull(val)
            ]
        )
    except Exception:
        mean_before_float = 0
        mean_after_float = 0
        max_after_float = 0

    # Check if the max value is 0, then set the flag = 1 else 0
    zero_flag = 1

    if max_after_float > 0:
        zero_flag = 0

    # If the length of float type is 0, then return default values else compute the statistics
    if len(float_type_data) > 0:
        _mean, _variance, _skew, _kurtosis, _min, _max, _sum = compute_stats(
            float_type_data
        )
        return (
            float_type_data,
            float_type_ratio,
            _mean,
            _median,
            _variance,
            _skew,
            _kurtosis,
            _min,
            _max,
            _sum,
            mean_before_float,
            mean_after_float,
            max_after_float,
            zero_flag,
        )
    else:
        return (
            float_type_data,
            float_type_ratio,
            0,
            0,
            0,
            0,
            -3,
            0,
            0,
            0,
            mean_before_float,
            mean_after_float,
            max_after_float,
            zero_flag,
        )


# ====================================================================
# checkDate:
#  - Validate if the input data is of date/datetime format
#  - Preprocess and check the string against the pattern and return flag
# Parameters:
#     strs - input data
# ====================================================================
def checkDate(strs) -> int:
    date_pattern = " \d{4}-[0-1][0-9]-[0-3][0-9](-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{4}-[0-3][0-9]-[0-1][0-9](-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | [0-1][0-9]-\d{4}-[0-3][0-9](-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | [0-3][0-9]-\d{4}-[0-1][0-9](-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | [0-1][0-9]-[0-3][0-9]-\d{4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | [0-3][0-9]-[0-1][0-9]-\d{4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-\d{1,2}-\d{4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{4}-\d{1,2}-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-\d{4}-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{2,4}-(\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{2,4}-\d{1,2}-(\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | (\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+-\d{2,4}-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)*  | (\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+-\d{1,2}-\d{2,4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)*  | \d{1,2}-(\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+-\d{2,4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-\d{2,4}-(\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)*  | \d{2,4}-(\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)*  | \d{2,4}-\d{1,2}-(\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | (\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+-\d{2,4}-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | (\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+-\d{1,2}-\d{2,4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-(\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+-\d{2,4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-\d{2,4}-(\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{2,4}-(\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{2,4}-(\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | (\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+-\d{2,4} (-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | (\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+-\d{2,4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-(\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-(\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | (\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | (\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+-\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{2,4}-(\\bjanuary\\b|\\bfebruary\\b|\\bmarch\\b|\\bapril\\b|\\bmay\\b|\\bjune\\b|\\bjuly\\b|\\baugust\\b|\\bseptember\\b|\\boctober\\b|\\bnovember\\b|\\bdecember\\b)+-\d{2,4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{2,4}-(\\bjan\\b|\\bfeb\\b|\\bmar\\b|\\bapr\\b|\\bmay\\b|\\bjun\\b|\\bjul\\b|\\baug\\b|\\bsep\\b|\\bsept\\b|\\boct\\b|\\bnov\\b|\\bdec\\b)+-\d{2,4}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}-days-\d{1,2}:\d{1,2}:\d{1,2}(-\d{1,2}:\d{1,2}(:\d{1,2})*(z)*[-\d{0,3}]*(AM|PM|CDT|EDT|IST)*)* | \d{1,2}h[-]*\d{1,2}m | \d{1,2}:\d{2}[:|-]+\d{2} | \d{1,2}:\d{2}[-]*(AM|PM|CDT|EDT|IST)* | (FY|FQ)+[-]*\d{2,4} | \d+[-]*(year[s]*|month[s]*|day[s]*|week[s]*|year[s]*|hour[s]|minute[s]|second[s])+ | \d{1,2}-\d{2}-\d{2}[-]*(AM|PM|CDT|EDT|IST)* | \d{1,2}:\d{2}-(AM|PM|CDT|EDT|IST)+-\d{1,2}:\d{2}-(AM|PM|CDT|EDT|IST)+ | \b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)Z\b | \b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)Z\b"

    # Preprocess the text for pattern matching
    strs = (
        str(strs)
        .replace("/", " ")
        .replace(",", " ")
        .replace(".", " ")
        .replace(" ", "-")
    )
    strs = re.sub(string=strs, pattern="-+", repl="-")

    # Match the text with date pattern and return 1 or 0 based on matching
    matched = re.match(string=" " + strs + " ", pattern=date_pattern, flags=re.I)
    return 1 if matched else 0


# ====================================================================
# checkOtherDate:
#  - Match the text with day pattern and return 1 or 0 based on matching
# Parameters:
#     strs - input data
# ====================================================================
def checkOtherDate(strs) -> int:
    # Pattern for the day checks
    days_abbr = [
        "saturday",
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "october",
        "november",
        "december",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
    ]
    days_abbr_patt = "\\b" + "\\b|\\b".join(days_abbr) + "\\b"

    # Match the text with day pattern and return 1 or 0 based on matching
    day_check = re.findall(string=strs, pattern=days_abbr_patt, flags=re.I)
    return 1 if len(day_check) > 0 else 0


# ====================================================================
# checkDateRange:
#  - Match the date range and return 1 or 0 based on condition
# Parameters:
#     strs - input data
# ====================================================================
def checkDateRange(strs) -> int:
    try:
        if int(strs) >= minRange and int(strs) <= maxRange:
            return 1
        else:
            return 0
    except Exception:
        return 0


# ====================================================================
# checkRange:
#  - Match the range pattern and return the flag based on the match condition
# Parameters:
#     strs - input data
# ====================================================================
def checkRange(vals):
    range_data = re.findall(
        pattern=settings.DI_CONFIG["PREPROCESS_CONSTANT"]["RANGE_PATTERN"], string=str(vals)
    )
    if len(range_data) > 0 and float(range_data[0][1]) >= float(range_data[0][0]):
        return 1


# ====================================================================
# upper_char_len_in_cells:
#  -  Check the total number of upper case characters
# Parameters:
#     values - input data
# ====================================================================
def upper_char_len_in_cells(values: str) -> int:
    return len(re.findall("[A-Z]", values)) / len(values)


# ====================================================================
# lower_char_len_in_cells:
#  -  Check the total number of lower case characters
# Parameters:
#     values - input data
# ====================================================================
def lower_char_len_in_cells(values: str) -> int:
    return len(re.findall("[a-z]", values)) / len(values)


# ====================================================================
# get_word_length:
#  -  Check the word length
# Parameters:
#     val - input data
# ====================================================================
def get_word_length(val: str) -> int:
    return len(val.split(" "))


def get_char_length(val: str) -> int:
    """
    - Get character length of a value
    Parameters
    ----------
    val (str): column values as string
    Returns
    -------
    int: total character length

    """
    return len(str(val))


# ====================================================================
# lexical_matching:
#  - Check if the cleaned data is empty
#  - Code should be calculated at Element level and not at word level
#  - Match each text with the TRIE regex on nltk word list
#  - Get the total matched text with english dictionary to total data
# Parameters:
#     cleaned_data - list of input data
# ====================================================================
def lexical_matching(cleaned_data: list) -> float:
    final_score = []

    # Check if the cleaned data is empty
    if len(cleaned_data) == 0:
        return 0
    else:
        words_freq = Counter(cleaned_data)

        # Code should be calculated at Element level and not at word level
        for search_word in words_freq.keys():
            bool_score = 0
            for words in search_word.lower().split():
                if tre.has(words):
                    bool_score = 1
                    break
            final_score.append(bool_score * words_freq[search_word])

        # Get the total matched text with english dictionary to total data
        return sum(final_score) / len(cleaned_data)


# ====================================================================
# alphanum_flag_creation:
#  - Change in the feature for alphanumeric features
#  -
# Parameters:
#     values - list of input data
# ====================================================================
def alphanum_flag_creation(values, alpha, numeric):
    # Change in the feature for alphanumeric features
    if alpha == 1:
        return 1
    elif numeric == 1:
        return 0
    else:
        return lexical_matching(values)


# ====================================================================
# url_identification_flag:
#  - Check the length of total urls present in text
# Parameters:
#     text - input data
# ====================================================================
def url_identification_flag(text: str) -> list:
    return [len(re.findall(settings.DI_CONFIG["PREPROCESS_CONSTANT"]["URL_PATTERN"], str(text)))]


# ====================================================================
# additional_features:
#  - Subset values for the alphanumeric, alpha, numeric and others type
#  - Calculate the upper and lower case characters and ratio and mean values
#  - Iterate through each elements and get the int, float, range type, date data for feature creation
#  - Get the ratio of the various features based on total values
#  - Get the statistical values for the Integer, Float, Date type, word length
#  - Get the url length and alphanum dictionary feature for each values
# Parameters:
#   col_values - list of input data
#   date_samples - number of rows for the date patten matching
# ====================================================================
def additional_features(col_values: list, date_samples: int = 1000) -> list:
    # Define the values for storing the features
    numeric_type = []
    int_type = []
    float_type = []
    alpha_type = []
    alphanum_type = []
    others_type = []
    # upper_case = []
    # lower_case = []
    range_type = []
    date_type = []

    # Defining the default values for the feature creation
    (
        mean_before_int,
        mean_before_float,
        mean_after_float,
        max_after_float,
        zero_flag,
        mean_uppercase,
        mean_lowercase,
    ) = 0, 0, 0, 0, 0, 0, 0
    (
        int_mean,
        int_variance,
        int_skew,
        int_kurtosis,
        int_min,
        int_max,
        int_sum,
        int_median,
    ) = 0, 0, 0, -3, 0, 0, 0, 0
    (
        float_mean,
        float_variance,
        float_skew,
        float_kurtosis,
        float_min,
        float_max,
        float_sum,
        float_median,
    ) = 0, 0, 0, -3, 0, 0, 0, 0
    (
        alphaNumRatio,
        numericRatio,
        alphaRatio,
        otherRatio,
        dateRatio,
        intRatio,
        floatRatio,
    ) = 0, 0, 0, 0, 0, 0, 0
    (
        wordlen_mean,
        wordlen_variance,
        wordlen_skew,
        wordlen_kurtosis,
        wordlen_min,
        wordlen_max,
        wordlen_sum,
        wordlen_median,
    ) = 0, 0, 0, 0, 0, 0, 0, 0
    url_mean, alphanum_dict_ratio = 0, 0

    # subset the values which is not empty for the feature creation
    col_values = [values for values in col_values if len(values) > 0]
    total_vals = len(col_values)

    # Subset values for the alphanumeric, alpha, numeric and others type
    log.info("Custom feature creation alphaAndNumericMatch started:%s", datetime.now())
    alphaNum = pseq(
        map(alphaAndNumericMatch, col_values), processes=core_count, partition_size=size
    )
    alphaNum = list(alphaNum)
    alpha_type = list(filter(lambda item: item == "alpha", alphaNum))
    alphanum_type = list(filter(lambda item: item == "alphanumeric", alphaNum))
    numeric_type = list(filter(lambda item: item == "numeric", alphaNum))
    others_type = list(filter(lambda item: item == "others", alphaNum))

    # Calculate the upper case characters and ratio and mean values
    log.info(
        "Custom feature creation upper and lower characters started:%s", datetime.now()
    )
    upper_case_ratio = pseq(
        map(upper_char_len_in_cells, col_values),
        processes=core_count,
        partition_size=size,
    )
    upper_case_ratio = list(upper_case_ratio)
    mean_uppercase = np.mean(upper_case_ratio) if len(upper_case_ratio) > 0 else 0

    # Calculate the lower case characters and ratio and mean values
    lower_case_ratio = pseq(
        map(lower_char_len_in_cells, col_values),
        processes=core_count,
        partition_size=size,
    )
    lower_case_ratio = list(lower_case_ratio)
    mean_lowercase = np.mean(lower_case_ratio) if len(lower_case_ratio) > 0 else 0

    # Iterate through each elements and get the integer type data for feature creation
    log.info("Custom feature creation checkInt started:%s", datetime.now())
    int_data = pseq(
        map(checkInt, col_values), processes=core_count, partition_size=size
    )
    # int_type = [int(col_values[idx].replace(',', '')) for idx, val in enumerate(int_data) if val == 1]
    int_type = [
        int(col_values[idx].replace(",", ""))
        for idx, val in enumerate(int_data)
        if val == 1
    ]
    # int_type = list(int_type)
    int_type = to_high_precision_array(int_type)

    # Iterate through each elements and get the float type data for feature creation
    log.info("Custom feature creation checkFloat started:%s", datetime.now())
    float_data = pseq(
        map(checkFloat, col_values), processes=core_count, partition_size=size
    )
    float_type = [
        float(col_values[idx].replace(",", ""))
        for idx, val in enumerate(float_data)
        if val == 1
    ]
    # float_type = list(float_type)
    float_type = to_high_precision_array(float_type)

    # Iterate through each elements and get the range type data for feature creation
    log.info("Custom feature creation checkRange started:%s", datetime.now())
    range_data = pseq(
        map(checkRange, col_values), processes=core_count, partition_size=size
    )
    range_type = list(filter(lambda item: item == 1, range_data))
    range_type = list(range_type)

    # Iterate through each elements and get the date type data for feature creation
    log.info("Custom feature creation checkDate started:%s", datetime.now())
    sub_values = col_values[:date_samples]

    # Iterate through each elements and get the date type data for feature creation
    date_data = pseq(
        map(checkDate, sub_values), processes=core_count, partition_size=size
    )
    date_data = list(date_data)

    # Iterate through each elements and get the other date type data for feature creation
    log.info("Custom feature creation checkOtherDate started:%s", datetime.now())
    day_data = pseq(
        map(checkOtherDate, sub_values), processes=core_count, partition_size=size
    )
    day_data = list(day_data)

    # Iterate through each elements and get the date range data for feature creation
    log.info("Custom feature creation DateRange started:%s", datetime.now())
    daterange_data = pseq(
        map(checkDateRange, sub_values), processes=core_count, partition_size=size
    )
    daterange_data = list(daterange_data)

    date_type = [
        max(date_data[val], day_data[val], daterange_data[val])
        for val in range(len(date_data))
    ]

    # Get the ratio of the various features based on total values
    alphaNumRatio = len(alphanum_type) / total_vals if total_vals > 0 else 0
    numericRatio = len(numeric_type) / total_vals if total_vals > 0 else 0
    alphaRatio = len(alpha_type) / total_vals if total_vals > 0 else 0
    otherRatio = len(others_type) / total_vals if total_vals > 0 else 0
    dateRatio = np.mean(date_type) if total_vals > 0 else 0
    intRatio = len(int_type) / total_vals if total_vals > 0 else 0
    floatRatio = len(float_type) / total_vals if total_vals > 0 else 0
    rangeRatio = len(range_type) / total_vals if total_vals > 0 else 0

    log.info("Custom feature creation Integer features:%s", datetime.now())

    # Get the statistical values for the Integer type
    int_median = np.median(int_type)
    int_median = int_median if pd.notnull(int_median) else 0

    try:
        mean_before_int = np.mean([len(str(val)) for val in int_type])
    except Exception:
        # mean_before_int = np.NaN
        mean_before_int = np.nan

    mean_before_int = mean_before_int if pd.notnull(mean_before_int) else 0

    if len(int_type) > 0:
        int_mean, int_variance, int_skew, int_kurtosis, int_min, int_max, int_sum = (
            compute_stats(int_type)
        )

    int_mean = int_mean if pd.notnull(int_mean) else 0
    int_variance = int_variance if pd.notnull(int_variance) else 0
    int_skew = int_skew if pd.notnull(int_skew) else 0
    int_kurtosis = int_kurtosis if pd.notnull(int_kurtosis) else -3
    int_min = int_min if pd.notnull(int_min) else 0
    int_max = int_max if pd.notnull(int_max) else 0
    int_sum = int_sum if pd.notnull(int_sum) else 0

    log.info("Custom feature creation Float features:%s", datetime.now())

    # Get the statistical values for the Float type
    float_median = np.median(float_type)
    float_median = float_median if pd.notnull(float_median) else 0

    try:
        float_elem = [
            str(float(val)).split(".") for val in float_type if pd.notnull(val)
        ]
        mean_before_float = np.mean([len(val[0]) for val in float_elem])
        mean_after_float = np.mean([len(val[1]) for val in float_elem if len(val) > 1])
        max_after_float = max([float(val[1]) for val in float_elem if len(val) > 1])
    except Exception:
        # max_after_float = np.NaN
        max_after_float = np.nan
        mean_before_float, mean_after_float = 0, 0

    # Get the Float related values before and after float types
    orig_max_after_float = max_after_float
    max_after_float = max_after_float if pd.notnull(max_after_float) else 0

    if pd.isnull(orig_max_after_float) or max_after_float > 0:
        zero_flag = 0
    else:
        zero_flag = 1

    if len(float_type) > 0:
        (
            float_mean,
            float_variance,
            float_skew,
            float_kurtosis,
            float_min,
            float_max,
            float_sum,
        ) = compute_stats(float_type)

    float_mean = float_mean if pd.notnull(float_mean) else 0
    float_variance = float_variance if pd.notnull(float_variance) else 0
    float_skew = float_skew if pd.notnull(float_skew) else 0
    float_kurtosis = float_kurtosis if pd.notnull(float_kurtosis) else -3
    float_min = float_min if pd.notnull(float_min) else 0
    float_max = float_max if pd.notnull(float_max) else 0
    float_sum = float_sum if pd.notnull(float_sum) else 0

    # Get the statistical values for the word length
    log.info("Custom feature creation word length features:%s", datetime.now())
    word_len_data = pseq(
        map(get_word_length, col_values), processes=core_count, partition_size=size
    )
    word_len_data = list(word_len_data)

    if len(word_len_data) > 0:
        (
            wordlen_mean,
            wordlen_variance,
            wordlen_skew,
            wordlen_kurtosis,
            wordlen_min,
            wordlen_max,
            wordlen_sum,
        ) = compute_stats(word_len_data)
        wordlen_median = np.median(word_len_data)
        wordlen_max = np.max(word_len_data)

    # Get the statistical values for the character length
    char_len_data = pseq(
        map(get_char_length, col_values), processes=core_count, partition_size=size
    )
    char_len_data = list(char_len_data)
    if len(char_len_data) > 0:
        charlen_max = np.max(char_len_data)
    else:
        charlen_max = 0

    # Get the url length for each values
    log.info("Custom feature creation URL Identification features:%s", datetime.now())
    url_len_data = pseq(
        map(url_identification_flag, col_values),
        processes=core_count,
        partition_size=size,
    )
    url_len_data = list(url_len_data)
    url_mean = np.mean(url_len_data) if total_vals > 0 else 0

    # Alphanum Dictionary Flag feature Creation
    log.info(
        "Custom feature creation Alphanum Dictionary Flag features:%s", datetime.now()
    )
    alphanum_dict_ratio = alphanum_flag_creation(col_values, alphaRatio, numericRatio)

    log.info("Custom feature creation case based features:%s", datetime.now())

    return [
        total_vals,
        alphaNumRatio,
        numericRatio,
        alphaRatio,
        otherRatio,
        dateRatio,
        intRatio,
        floatRatio,
        rangeRatio,
        int_mean,
        int_variance,
        int_skew,
        int_kurtosis,
        int_min,
        int_max,
        int_sum,
        int_median,
        mean_before_int,
        float_mean,
        float_variance,
        float_skew,
        float_kurtosis,
        float_min,
        float_max,
        float_sum,
        float_median,
        zero_flag,
        mean_before_float,
        mean_after_float,
        max_after_float,
        mean_uppercase,
        mean_lowercase,
        wordlen_mean,
        wordlen_variance,
        wordlen_skew,
        wordlen_kurtosis,
        wordlen_min,
        wordlen_max,
        wordlen_sum,
        wordlen_median,
        url_mean,
        alphanum_dict_ratio,
        charlen_max,
    ]


# ====================================================================
# extract_addl_feats:
#  - Creating of additional/custom features
#  - Call the additional features for the input values
#  - Iterate through created features and store it in the feature dictionary
# Parameters:
#   col_values - list of input data
#   features - dictionary of features
# ====================================================================
def extract_addl_feats(col_values: list, features: OrderedDict):
    # Creating of additional/custom features
    feats_name = [
        "total_vals",
        "alphaNumRatio",
        "numericRatio",
        "alphaRatio",
        "otherRatio",
        "dateRatio",
        "intRatio",
        "floatRatio",
        "rangeRatio",
        "int_mean",
        "int_variance",
        "int_skew",
        "int_kurtosis",
        "int_min",
        "int_max",
        "int_sum",
        "int_median",
        "mean_before_int",
        "float_mean",
        "float_variance",
        "float_skew",
        "float_kurtosis",
        "float_min",
        "float_max",
        "float_sum",
        "float_median",
        "zero_flag",
        "mean_before_float",
        "mean_after_float",
        "max_after_float",
        "mean_uppercase",
        "mean_lowercase",
        "wordlen_mean",
        "wordlen_variance",
        "wordlen_skew",
        "wordlen_kurtosis",
        "wordlen_min",
        "wordlen_max",
        "wordlen_sum",
        "wordlen_median",
        "url_mean",
        "alphanum_dict_ratio",
        "charlen_max",
    ]

    # Call the additional features for the input values
    start_time = datetime.now()
    log.info("Custom feature creation started:%s", start_time)
    feats_list = additional_features(col_values)
    end_time = datetime.now()
    log.info("Custom feature creation completed:%s", end_time)
    log.info("Total time taken:%s", end_time - start_time)

    # Iterate through created features and store it in the feature dictionary
    for iters, name in enumerate(feats_name):
        features[name] = feats_list[iters]
