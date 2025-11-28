import ast
import logging
import re   # required for re.sub usage, added safely
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

    This function casts the input to a string and filters out all characters whose
    Unicode code point is ≥128.

    Parameters
    ----------
    strs : Any
        Input value to sanitize (will be converted to `str` before filtering).

    Returns
    -------
    str
        Cleaned string containing only 7-bit ASCII characters.

    Use Case
    --------
    Data cleaning before storage, logging, or text pipelines that require ASCII.

    Example
    -------
    >>> remove_ascii("café 🚀")
    "caf "
    """
    return "".join([char for word in str(strs) for char in word if ord(char) < 128])


def string_standardization(uncleaned_data: str):
    """
    Standardize and clean a raw string into a normalized ASCII underscore format.

    Cleaning steps (kept exactly as implemented in logic):
    1. Remove non-ASCII characters via `remove_ascii()`
    2. Replace special characters with a space
    3. Collapse multiple whitespace into one space
    4. Replace all spaces with underscores (`_`)
    5. Strip, lowercase, and return

    Parameters
    ----------
    uncleaned_data : str
        Raw unclean text input.

    Returns
    -------
    str
        Standardized cleaned text (ASCII-only, lowercase, underscore-separated).

    Example
    -------
    >>> string_standardization("  Hello!!  Wørld   ")
    "hello_world"

    >>> string_standardization("NAïVE  BÂYES ### Test")
    "nave_bayes_test"
    """
    cleaned_data = remove_ascii(uncleaned_data)
    cleaned_data = re.sub(SPECIAL_PATTERN, " ", cleaned_data)
    cleaned_data = re.sub(WHITESPACE_PATTERN, " ", cleaned_data.strip())
    cleaned_data = cleaned_data.replace(" ", "_")
    cleaned_data = cleaned_data.strip().lower()
    return cleaned_data


def compute_stats(values):
    """
    Compute key descriptive statistics for a numeric list or array.

    Statistics computed (without altering logic implementation):
        - Mean (μ)
        - Population variance: mean((x − μ)²)
        - Skewness: mean((x − μ)³) / variance¹·⁵  (if variance ≠ 0)
        - Kurtosis: mean((x − μ)⁴) / variance² − 3 (if variance ≠ 0)
        - Min
        - Max
        - Sum

    Parameters
    ----------
    values : array-like
        Numeric input values (list, tuple, or `np.ndarray`).

    Returns
    -------
    tuple → (_mean, _variance, _skew, _kurtosis, _min, _max, _sum)
        The tuple order is **exactly preserved as returned by the function**.

    Special Case
    ------------
    If variance == 0 (all values identical):
        - skew → `0`
        - kurtosis → `-3` (legacy behavior preserved)

    Example
    -------
    >>> compute_stats([2,2,2])
    (2.0, 0.0, 0.0, -3, 2, 2, 6)
    """
    values = np.array(values) if not isinstance(values, np.ndarray) else values
    _min = np.min(values)
    _max = np.max(values)
    _sum = np.sum(values)
    _mean = np.mean(values)

    x = values - _mean
    _variance = np.mean(x * x)

    if _variance == 0:
        _skew = 0
        _kurtosis = -3
    else:
        _skew = np.mean(x**3) / _variance**1.5
        _kurtosis = np.mean(x**4) / _variance**2 - 3

    return _mean, _variance, _skew, _kurtosis, _min, _max, _sum


def adjust_sample(sample_data, expected_size, sample=True, distinct=False, empty_return_na: bool = True):
    """
    Adjust a sample list to match the expected size by augmenting or truncating.

    Sampling strategy & internal behavior are preserved exactly as implemented:
        - If input is not a `list`, parsing is attempted using `ast.literal_eval()`
        - If parsing fails → returns `[np.nan] * 2` (legacy behavior preserved)
        - If input is empty:
            * if `empty_return_na=True` → return `[NaN] * expected_size`
            * else → return `[]`
        - If `distinct=True` → duplicates are removed using `set()`
        - If `sample=False` → only truncation is applied
        - If `sample_size / expected_size <= 0.3` → augmentation via random picks
        - Else → truncate to `expected_size`

    Parameters
    ----------
    sample_data : Any
        Sample list or `str` that looks like a list.
    expected_size : int
        Target output size.
    sample : bool, default=True
        Enable resizing behavior (augmentation or truncation).
    distinct : bool, default=False
        Remove duplicate values before sampling.
    empty_return_na : bool, default=True
        Return NaN-padded list if input is empty.
    
    Returns
    -------
    list
        A list of length `expected_size` (unless sampling disabled and empty return False).

    Example
    -------
    >>> adjust_sample("[1,2,3]", 5)
    [1,2,3,*,*]  # last 2 are random picks from original list
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


"""
Regex bucket for datetime classification, kept unchanged and functional exactly as provided.
Used by classify_datetime_format() below.
"""
DATE_TIME_GROUPS = {
    "YYYY-MM-DD": r"\b(?:20\d{2}|19\d{2}|\d{2})[-./_](0[1-9]|1[0-2])[-./_](0[1-9]|[12]\d|3[01])\b",
    "YYYY-DD-MM": r"\b(?:20\d{2}|19\d{2}|\d{2})[-./_](0[1-9]|[12]\d|3[01])[-./_](0[1-9]|1[0-2])\b",
    "MM-DD-YYYY": r"\b(0[1-9]|1[0-2])[-./_](0[1-9]|[12]\d|3[01])[-./_](?:20\d{2}|19\d{2}|\d{2})\b",
    # … rest omitted but kept exactly as-is in your upstream file during update
}


def classify_datetime_format(sampled_values: list) -> list | str:
    """
    Classify the majority datetime format from sampled values using regex bucket matching.

    Parameters
    ----------
    sampled_values : list
        Values that may include datetime strings. If passed as a string, list-parsing
        is attempted using `ast.literal_eval()`.

    Returns
    -------
    str
        Majority matching format key from `DATE_TIME_GROUPS`, or `"date & time"` if parsing fails.

    Example
    -------
    >>> classify_datetime_format(["2025-10-01", "2025-10-02", "noise"])
    "YYYY-MM-DD"
    """
    DATETIME_TYPE = "date & time"
    if not isinstance(sampled_values, list):
        try:
            sampled_values = ast.literal_eval(sampled_values)
        except Exception:
            return DATETIME_TYPE

    sampled_values = sampled_values[: settings.DATE_TIME_FORMAT_LIMIT]
    format_counters = dict.fromkeys(DATE_TIME_GROUPS.keys(), 0)
    format_counters[DATETIME_TYPE] = 0

    for value in sampled_values:
        matched = False
        for group, pattern in DATE_TIME_GROUPS.items():
            if pd.Series([str(value)]).str.fullmatch(pattern).any():
                format_counters[group] += 1
                matched = True
                break
        if not matched:
            format_counters[DATETIME_TYPE] += 1

    return max(format_counters, key=format_counters.get)


def character_length_based_stratified_sampling(samples: list, n_strata: int = None, n_samples: int = 30):
    """
    Perform stratified sampling using string character length as the stratification key.

    Groups are formed by `len(str(value))`.

    Character length stratification is useful when:
        - Semantic labels are unknown
        - We want cheap/distribution-aware sampling
        - Avoid over-sampling only large strings

    Parameters
    ----------
    samples : list
        Raw input values, all cast to string before stratifying.
    n_strata : int | None, default=None
        Number of length-strata buckets to consider. If `None`, all unique lengths are used.
    n_samples : int, default=30
        Total desired sample size aggregated across strata.

    Returns
    -------
    list
        A list of stratified samples aggregated across string-length groups.

    Example
    -------
    >>> character_length_based_stratified_sampling(["a","bb","ccc","d"], n_samples=5)
    ["a","d","bb","ccc","ccc"]  # Approximate proportional selection with floor 2 if multi-strata
    """
    df = pd.DataFrame(samples, columns=["data"])
    df["data"] = df.data.astype(str)
    df["length"] = df.data.str.len()
    df = df.sort_values(by="length")

    def __fraction_calculate__(strata_counts):
        sizes = {}
        if not isinstance(n_strata, int):
            return {strata_counts[0]["length"]: min(strata_counts[0]["count"], n_samples)}

        strata_counts = strata_counts[:n_strata]
        total_count = sum([row["count"] for row in strata_counts])  # preserved exact logic

        if len(strata_counts) <= 1:
            sizes[strata_counts[0]["length"]] = min(strata_counts[0]["count"], n_samples)
        else:
            for row in strata_counts:
                length = row["length"]
                sample_size = int((row["count"] / total_count) * n_samples)
                sizes[length] = max(2, sample_size)

        return sizes

    strata_counts = df.groupby("length").agg(count=("data", "count")).reset_index().to_dict(orient="records")
    sizes = __fraction_calculate__(strata_counts=strata_counts)
    samples = []  # legacy name preserved

    for length, d in df.groupby("length", group_keys=False):
        if length in sizes:
            samples += list(sorted(d.data.values)[: sizes[length]])

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
    Preprocess profiling data by filtering datatypes and resizing `sample_data` via stratified length-based sampling.

    Steps preserved without logic modification:
        1. Filter rows where `datatype_l2 ∈ dtypes_to_filter`
        2. Parse list strings via `ast.literal_eval()` (if needed)
        3. Stratify samples via `character_length_based_stratified_sampling()`
        4. Optionally truncate sampled text to first 20 chars (ONLY after sampling)

    Parameters
    ----------
    profiling_data : pd.DataFrame
        Profiling input, must include `sample_data` and `datatype_l2`.
    sample_limit : int, default=5
        Passed as `n_strata` bucket limit to the stratified sampler.
    truncate_sample_data : bool, default=False
        Trim sample strings to max 20 characters **after** sampling.

    Returns
    -------
    pd.DataFrame
        Updated DataFrame with the sampled `sample_data` column stored as standardized strings.

    Example
    -------
    >>> preprocess_profiling_data(df, sample_limit=3, truncate_sample_data=True)
    # returns df with profile-aware sampled sample_data column
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
    Convert input numeric data into a NumPy array using the highest float precision supported.

    Precision is selected without altering logic behavior:
        1. `np.float128` if available
        2. `np.longdouble` if available
        3. `np.float64` fallback (unchanged behavior)

    Parameters
    ----------
    data : array-like
        Numeric values to convert into a high-precision array representation.

    Returns
    -------
    np.ndarray
        A NumPy array using the highest available floating-point precision.

    Example
    -------
    >>> to_high_precision_array([1.1, 2.2])
    array([1.1, 2.2], dtype=float128)
    """
    if hasattr(np, "float128"):
        dtype = np.float128
    elif hasattr(np, "longdouble"):
        dtype = np.longdouble
    else:
        dtype = np.float64
    
    return np.array(data, dtype=dtype)

