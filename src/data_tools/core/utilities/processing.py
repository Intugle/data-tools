import logging
import re

import numpy as np

log = logging.getLogger(__name__)


SPECIAL_PATTERN = r'[^a-zA-Z0-9\s]'
WHITESPACE_PATTERN = r'\s{2,}'
ASCII_PATTERN = r'[^\x00-\x7F]'


def remove_ascii(strs) -> str:
    return ''.join([char for word in str(strs) for char in word if ord(char) < 128])


def string_standardization(uncleaned_data: str):
    cleaned_data = remove_ascii(uncleaned_data)
    cleaned_data = re.sub(SPECIAL_PATTERN, ' ', cleaned_data)
    cleaned_data = re.sub(WHITESPACE_PATTERN, ' ', cleaned_data.strip())
    cleaned_data = cleaned_data.replace(" ", "_")
    cleaned_data = cleaned_data.strip().lower()
    return cleaned_data


def compute_stats(values):
    
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
        _skew = np.mean(x ** 3) / _variance ** 1.5
        _kurtosis = np.mean(x ** 4) / _variance ** 2 - 3
    
    return _mean, _variance, _skew, _kurtosis, _min, _max, _sum


def adjust_sample(sample_data, expected_size, sample=True, distinct=False, empty_return_na: bool = True):
    
    if not isinstance(sample_data, list):
        try:
            sample_data = eval(sample_data)
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