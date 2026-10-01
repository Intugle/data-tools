import ast
import logging
import re

import numpy as np
import pandas as pd

from intugle.core import settings

log = logging.getLogger(__name__)


SPECIAL_PATTERN = r"[^a-zA-Z0-9\s]"
WHITESPACE_PATTERN = r"\s{2,}"
ASCII_PATTERN = r"[^\x00-\x7F]"


def remove_ascii(strs) -> str:
    """
    Remove all non-ASCII characters from the input.

    This function iterates over the input string and filters out any characters
    whose ASCII code is greater than or equal to 128. It is commonly used as a
    preprocessing step for data cleaning and standardization.

    Parameters
    ----------
    strs : Any
        Input value to process. It is cast to string before filtering.

    Returns
    -------
    str
        A string containing only ASCII characters.

    Example
    -------
    >>> remove_ascii("Café Münster")
    'Caf Mnster'
    """
    return "".join([char for word in str(strs) for char in word if ord(char) < 128])


def string_standardization(uncleaned_data: str):
    """
    Standardize a string by removing noise and normalizing formatting.

    The cleaning steps include:
    - Removing non-ASCII characters
    - Replacing special characters with spaces
    - Collapsing multiple whitespaces
    - Replacing spaces with underscores
    - Converting text to lowercase

    This function is useful for preparing strings for identifiers,
    column names, or normalized comparisons.

    Parameters
    ----------
    uncleaned_data : str
        Raw input string to clean and standardize.

    Returns
    -------
    str
        A cleaned, lowercase, underscore-separated string.

    Example
    -------
    >>> string_standardization("Hello, World!!  ")
    'hello_world'
    """
    cleaned_data = remove_ascii(uncleaned_data)
    cleaned_data = re.sub(SPECIAL_PATTERN, " ", cleaned_data)
    cleaned_data = re.sub(WHITESPACE_PATTERN, " ", cleaned_data.strip())
    cleaned_data = cleaned_data.replace(" ", "_")
    cleaned_data = cleaned_data.strip().lower()
    return cleaned_data


def compute_stats(values):
    """
    Compute basic statistical metrics for a numeric dataset.

    The following statistics are calculated:
    - Mean
    - Variance
    - Skewness
    - Kurtosis
    - Minimum
    - Maximum
    - Sum

    If the variance is zero, skewness is returned as 0 and kurtosis as -3,
    following statistical convention.

    Parameters
    ----------
    values : array-like
        Numeric values as a list or NumPy array.

    Returns
    -------
    tuple
        A tuple containing:
        (mean, variance, skewness, kurtosis, min, max, sum)

    Example
    -------
    >>> compute_stats([1, 2, 3])
    (2.0, 0.666..., 0.0, -1.5, 1, 3, 6)
    """
    # Converting the values to array format
    values = np.array(values) if not isinstance(values, np.ndarray) else values
    # Calculate the statistical results from the values
    _min = np.min(values)
    _max = np.max(values)
    _sum = np.sum(values)
    _mean = np.mean(values)

    x = values - _mean
    _variance = np.mean(x * x)

    # If the variance is 0 then return default value for skew and kurtosis
    if _variance == 0:
        _skew = 0
        _kurtosis = -3
    else:
        _skew = np.mean(x**3) / _variance**1.5
        _kurtosis = np.mean(x**4) / _variance**2 - 3

    return _mean, _variance, _skew, _kurtosis, _min, _max, _sum


def adjust_sample(sample_data, expected_size, sample=True, distinct=False, empty_return_na: bool = True):
    """
    Adjust a list of sample values to match an expected size.

    This function optionally:
    - Parses string representations of lists
    - Removes duplicates
    - Truncates samples
    - Augments small samples using random selection

    It is commonly used to normalize sample sizes for downstream processing.

    Parameters
    ----------
    sample_data : list or str
        Sample data as a list or a string representation of a list.
    expected_size : int
        Desired size of the output sample.
    sample : bool, optional
        Whether to sample or truncate data (default: True).
    distinct : bool, optional
        Remove duplicate values before sampling (default: False).
    empty_return_na : bool, optional
        Return NaN values when sample is empty (default: True).

    Returns
    -------
    list
        Adjusted list of samples with length up to expected_size.

    Example
    -------
    >>> adjust_sample([1, 2], expected_size=5)
    [1, 2, 2, 1, 1]
    """
    if not isinstance(sample_data, list):
        try:
            sample_data = ast.literal_eval(sample_data)
        except Exception:
            log.error("[!] Error when evaluating sample_data")
            return [np.nan] * 2

    sample_size = len(sample_data)

    if sample_size == 0:
        if empty_return_na:
            return [np.nan] * expected_size
        else:
            return []

    if distinct:
        sample_data = list(set(sample_data))

    if not sample:
        return sample_data[:expected_size]

    if sample_size / expected_size <= 0.3:
        sample_data = sample_data + list(np.random.choice(sample_data, expected_size - sample_size))

    else:
        sample_data = sample_data[:expected_size]

    return sample_data


DATE_TIME_GROUPS = {
    "YYYY-MM-DD": r"\b(?:20\d{2}|19\d{2}|\d{2})[-./_](0[1-9]|1[0-2])[-./_](0[1-9]|[12]\d|3[01])\b",
    "YYYY-DD-MM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-./_](0[1-9]|[12]\d|3[01])[-./_](0[1-9]|1[0-2])\b",
    "MM-DD-YYYY": r"\b(0[1-9]|1[0-2])[-./_](0[1-9]|[12]\d|3[01])[-./_](?:20\d{2}|19\d{2}|\d{2})\b",
    "DD-MM-YYYY": r"\b(0[1-9]|[12]\d|3[01])[-./_](0[1-9]|1[0-2])[-./_](?:20\d{2}|19\d{2}|\d{2})\b",
    "YYYY-MM-DDTHH:MM:SS": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\b",
    "YYYY-DD-MMTHH:MM:SS": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\b",
    "YYYY-MM-DDTHH:MM:SSZ": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)Z\b",
    "YYYY-DD-MMTHH:MM:SSZ": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)Z\b",
    "YYYY-MM-DDTHH:MM:SS.sssZ": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\.(\d{3})Z\b",
    "YYYY-DD-MMTHH:MM:SS.sssZ": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\.(\d{3})Z\b",
    "YYYY-MM-DDTHH:MM:SS.sss±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\.(\d{3})[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-DD-MMTHH:MM:SS.sss±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\.(\d{3})[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-MM-DDTHH:MM:SS.sss±HH": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\.(\d{3})[+-](0[0-9]|1[0-2])\b",
    "YYYY-DD-MMTHH:MM:SS.sss±HH": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\.(\d{3})[+-](0[0-9]|1[0-2])\b",
    "YYYY-MM-DDTHH:MM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)\b",
    "YYYY-DD-MMTHH:MM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)\b",
    "YYYY-MM-DDTHH:MMZ": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)Z\b",
    "YYYY-DD-MMTHH:MMZ": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)Z\b",
    "YYYY-MM-DDTHH:MM±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-DD-MMTHH:MM±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-MM-DDTHH:MM±HH": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[+-](0[0-9]|1[0-2])\b",
    "YYYY-DD-MMTHH:MM±HH": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[+-](0[0-9]|1[0-2])\b",
    "MM-DD-YYYY HH:MM AM/PM": r"\b(?:0[1-9]|1[0-2])[-/._]?(0[1-9]|[12]\d|3[01])[-/._]?(?:20\d{2}|19\d{2}|\d{2})\s+(0[0-9]|1[0-2])[:,.]?([0-5]\d)\s*([APMapm]{2})\b",
    "DD-MM-YYYY HH:MM AM/PM": r"\b(0[1-9]|[12]\d|3[01])[-/._]?(0[1-9]|1[0-2])[-/._]?(?:20\d{2}|19\d{2}|\d{2})\s+(0[1-9]|[1][0-2])[:,.]?([0-5]\d)\s*([APMapm]{2})\b",
    "MM-DD-YYYY HH:MM": r"\b(?:0[1-9]|1[0-2])[-/._]?(0[1-9]|[12]\d|3[01])[-/._]?(?:20\d{2}|19\d{2}|\d{2})\s+([01]\d|2[0-4])[:,.]?([0-5]\d)\b",
    "DD-MM-YYYY HH:MM": r"\b(?:0[1-9]|[12]\d|3[01])[-/._]?(0[1-9]|1[0-2])[-/._]?(?:20\d{2}|19\d{2}|\d{2})\s+([01]\d|2[0-4])[:,.]?([0-5]\d)\b",
    "HH:MM:SS +/-HH:MM": r"\b(?:[01]\d|2[0-4])[:,.](?:[0-5]\d)[:,.](?:[0-5]\d)\s?([+-]\d{2}:[0-5]\d)\b",
    "HH:MM +/-HH:MM": r"\b(?:[01]\d|2[0-4])[:,.](?:[0-5]\d)\s?([+-]\d{2}:[0-5]\d)\b",
    "Day of the Week, Month Day, Year": r"\b(?:[Ss]unday|[Mm]onday|[Tt]uesday|[Ww]ednesday|[Tt]hursday|[Ff]riday|[Ss]aturday|[Ss]un|[Mm]on|[Tt]ue|[Ww]ed|[Tt]hu|[Ff]ri|[Ss]at),?\s*?(?:[Jj]anuary|[Ff]ebruary|[Mm]arch|[Aa]pril|[Mm]ay|[Jj]une|[Jj]uly|[Aa]ugust|[Ss]eptember|[Oo]ctober|[Nn]ovember|[Dd]ecember|[Jj]an|[Ff]eb|[Mm]ar|[Aa]pr|[Mm]ay|[Jj]un|[Jj]ul|[Aa]ug|[Ss]ep|[Oo]ct|[Nn]ov|[Dd]ec)\s*?\d{1,2},?\s*?\d{4}\b",
    "Day of the Week, Month Day, Year, Time": r"\b(?:[Ss]unday|[Mm]onday|[Tt]uesday|[Ww]ednesday|[Tt]hursday|[Ff]riday|[Ss]aturday|[Ss]un|[Mm]on|[Tt]ue|[Ww]ed|[Tt]hu|[Ff]ri|[Ss]at),?\s*?(?:[Jj]anuary|[Ff]ebruary|[Mm]arch|[Aa]pril|[Mm]ay|[Jj]une|[Jj]uly|[Aa]ugust|[Ss]eptember|[Oo]ctober|[Nn]ovember|[Dd]ecember|[Jj]an|[Ff]eb|[Mm]ar|[Aa]pr|[Mm]ay|[Jj]un|[Jj]ul|[Aa]ug|[Ss]ep|[Oo]ct|[Nn]ov|[Dd]ec)\s*?\d{1,2},?\s*?\d{4},\s*?\d{1,2}:\d{2}\s*([APMapm]{2})?\b",
    "Month Day, Year, Time": r"\b(?:[Jj]anuary|[Ff]ebruary|[Mm]arch|[Aa]pril|[Mm]ay|[Jj]une|[Jj]uly|[Aa]ugust|[Ss]eptember|[Oo]ctober|[Nn]ovember|[Dd]ecember|[Jj]an|[Ff]eb|[Mm]ar|[Aa]pr|[Mm]ay|[Jj]un|[Jj]ul|[Aa]ug|[Ss]ep|[Oo]ct|[Nn]ov|[Dd]ec)\s*?\d{1,2},?\s*?\d{4},\s*?\d{1,2}:\d{2}\s*([APMapm]{2})?\b",
    "HH:MM:SS.sss": r"\b([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)\.(\d{3})\b",
    "HH:MM:SS.sss AM/PM": r"\b(?:0[0-9]|1[0-2])[:,.](?:[0-5][0-9])[:,.](?:[0-5][0-9])\.\d{3}\s*?[APap][Mm]\b",
    "HH:MM": r"\b([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)\b",
    "HH:MM AM/PM": r"\b(?:0[0-9]|1[0-2])[:,.](?:[0-5][0-9])\s*?[APap][Mm]\b",
    "HH:MM AM/PM (Timezone)": r"^(0[0-9]|1[0-2])[:,.][0-5][0-9]( ?[APap][Mm])\s*?\([A-Za-z0-9\s:+-]+\)$",
    "HH:MM (Timezone)": r"^(?:[01]\d|2[0-4])[:,.][0-5]\d\s*?\([A-Za-z0-9\s:+-]+\)$",
    "YYYY-MM-DDTHH:MM:SS±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-DD-MMTHH:MM:SS±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)[:,.](0[0-9]|[1-5]\d)[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-MM-DDTHH:MM AM/PM±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|1[0-2])[-/._](0[1-9]|[12]\d|3[01])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)\s*?( ?[APap][Mm])[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-DD-MMTHH:MM AM/PM±HHMM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-/._](0[1-9]|[12]\d|3[01])[-/._](0[1-9]|1[0-2])T([01]\d|2[0-4])[:,.](0[0-9]|[1-5]\d)\s*?( ?[APap][Mm])[+-](0[0-9]|1[0-2])(?::|\.|,)?(0[0-9]|[1-5]\d)\b",
    "YYYY-MM-DD HH:MM:SS": r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
}


def classify_datetime_format(sampled_values: list) -> list | str:
    """
    - Classify the datetime format of a given list of column values.

    Parameters
    ----------
    column_values (list): List of values from a column.
    num_samples (int): Number of values to sample for classification.

    Returns
    -------
    The majority datetime format group.
    """
    DATETIME_TYPE = "date & time"
    if not isinstance(sampled_values, list):
        try:
            sampled_values = ast.literal_eval(sampled_values)
        except Exception:
            return DATETIME_TYPE

    sampled_values = sampled_values[: settings.DATE_TIME_FORMAT_LIMIT]

    format_counters = dict.fromkeys(DATE_TIME_GROUPS.keys(), 0)

    # Add "other" as a separate group
    format_counters[DATETIME_TYPE] = 0

    # Count occurences of each date-time format group in sampled values
    for value in sampled_values:
        matched = False
        for group, pattern in DATE_TIME_GROUPS.items():
            if pd.Series([str(value)]).str.fullmatch(pattern).any():
                format_counters[group] += 1
                matched = True
                break
        if not matched:
            format_counters[DATETIME_TYPE] += 1

    # Determine the majority format group
    majority_format_group = max(format_counters, key=format_counters.get)

    return majority_format_group


def character_length_based_stratified_sampling(samples: list, n_strata: int = None, n_samples: int = 30):
    """
    Perform stratified sampling based on string length.

    Samples are grouped by character length, and each group contributes
    proportionally to the final sample set. This ensures diversity in
    string lengths and avoids bias toward short or long values.

    Parameters
    ----------
    samples : list
        List of sample values.
    n_strata : int, optional
        Maximum number of length-based strata to consider.
    n_samples : int, optional
        Total number of samples to return (default: 30).

    Returns
    -------
    list
        Stratified subset of samples.

    Example
    -------
    >>> character_length_based_stratified_sampling(["a", "abcd", "abcdef"], n_samples=2)
    ['a', 'abcd']
    """
    df = pd.DataFrame(samples, columns=["data"])
    df["data"] = df.data.astype(str)
    df["length"] = df.data.str.len()
    df = df.sort_values(by="length")

    def __fraction_calculate__(strata_counts):
        sizes = {}
        strata_counts = strata_counts[:n_strata]
        total_count = sum([row["count"] for row in strata_counts])
        if len(strata_counts) <= 1:
            sizes[strata_counts[0]["length"]] = min(strata_counts[0]["count"], n_samples)
        else:
            for row in strata_counts:
                count_per_strata = row["count"]
                length = row["length"]
                sample_size = int((count_per_strata / total_count) * n_samples)
                sample_size = max(2, sample_size)
                sizes[length] = sample_size

        return sizes

    strata_counts = df.groupby("length").agg(count=("data", "count")).reset_index().to_dict(orient="records")
    sizes = __fraction_calculate__(strata_counts=strata_counts)
    samples = []
    for length, d in df.groupby("length", group_keys=False):
        if length in sizes:
            samples += sorted(d.data.values)[: sizes[length]]

    return samples


def preprocess_profiling_data(
    profiling_data: pd.DataFrame,
    sample_limit: int = 5,
    dtypes_to_filter=[
        "dimension",
    ],
    truncate_sample_data: bool = False,
) -> pd.DataFrame:
    """
    get the required profiling data with processed sample data
    """
    if dtypes_to_filter:
        profiling_data = profiling_data.loc[profiling_data.datatype_l2.isin(dtypes_to_filter)].reset_index(drop=True)

    def __sample_process__(sample_data, limit=5):
        try:
            if isinstance(sample_data, str):
                sample_data = ast.literal_eval(sample_data)

            if truncate_sample_data:
                sample_data = [str(sample)[:20] for sample in sample_data]

        except Exception as ex:
            log.error(f"[!] Error while sampling: {ex}")

        if len(sample_data) != 0:
            sample_data = character_length_based_stratified_sampling(
                samples=sample_data, n_strata=limit, n_samples=int(settings.LLM_SAMPLE_LIMIT)
            )

        return sample_data

    profiling_data["sample_data"] = profiling_data["sample_data"].apply(__sample_process__, limit=sample_limit)

    profiling_data["sample_data"] = profiling_data["sample_data"].astype(str)

    return profiling_data


def to_high_precision_array(data):
    """
    Converts input data to a NumPy array with the highest available floating-point precision.

    Priority: float128 > longdouble > float64

    Parameters:
        data: array-like
            The data to convert.

    Returns:
        np.ndarray
            A NumPy array with the highest available float precision.
    """

    if hasattr(np, "float128"):  # Works on most Unix-like systems
        dtype = np.float128
    elif hasattr(np, "longdouble"):  # Often higher precision than float64
        dtype = np.longdouble
    else:
        dtype = np.float64  # Fallback
    
    return np.array(data, dtype=dtype)
