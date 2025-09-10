import numpy as np
import pandas as pd

from intugle.core.semantic_search.models import RelevancyCategory


def relevancy_adder(
    result: pd.DataFrame,
    relevancy_scores: dict,
    o_column="relevancy",
    i_column="score",
) -> pd.DataFrame:

    # Add relevancy to each terms identified
    result[o_column] = np.where(
        result[i_column] >= relevancy_scores[RelevancyCategory.MOST_RELEVANT],
        RelevancyCategory.MOST_RELEVANT,
        np.where(
            np.logical_and(
                result[i_column] >= relevancy_scores[RelevancyCategory.RELEVANT],
                result[i_column] < relevancy_scores[RelevancyCategory.MOST_RELEVANT],
            ),
            RelevancyCategory.RELEVANT,
            np.where(
                np.logical_and(
                    result[i_column] >= relevancy_scores[RelevancyCategory.LESS_RELEVANT],
                    result[i_column] < relevancy_scores[RelevancyCategory.RELEVANT],
                ),
                RelevancyCategory.LESS_RELEVANT,
                RelevancyCategory.NON_RELEVANT,
            ),
        ),
    )
    return result


def batched(data: pd.DataFrame, n):
    for index in range(0, data.shape[0], n):
        yield data[index : index + n]
