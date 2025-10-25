import json
import logging
import re

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from intugle.parser.manifest import Manifest

log = logging.getLogger(__name__)


def batched(data: Any, n):
    for index in range(0, len(data), n):
        yield data[index : index + n]


def colbert_score_numpy(
    query_embeddings: np.ndarray, doc_embeddings: np.ndarray
) -> float:
    """
    ColBERT score using NumPy.

    Args:
        query_embeddings: np.ndarray of shape (q_len, dim)
        doc_embeddings: np.ndarray of shape (d_len, dim)

    Returns:
        float: ColBERT relevance score
    """
    # Normalize
    query_norm = query_embeddings / np.linalg.norm(
        query_embeddings, axis=1, keepdims=True
    )
    doc_norm = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)

    # Dot product matrix (q_len x d_len)
    similarity_matrix = np.dot(query_norm, doc_norm.T)

    # MaxSim for each query token
    max_similarities = np.max(similarity_matrix, axis=1)

    # Sum of max similarities
    score = np.sum(max_similarities)

    return float(score) / len(query_embeddings)


def manual_concept_extraction(ai_msg):
    try:
        concepts = json.loads(ai_msg.content)
        if isinstance(concepts, list) and all(isinstance(c, str) for c in concepts):
            return concepts
        else:
            log.info("Warning: JSON was parsed but did not return a list of strings.")
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        log.info(f"Primary JSON parsing failed: {e}")

    # --- Fallback strategy ---
    try:
        raw_text = getattr(ai_msg, "content", "")
        matches = re.findall(r"\[(.*?)\]", raw_text, re.DOTALL)
        if matches:
            items = re.findall(r'"([^"]+)"', matches[0])
            return items
        else:
            log.info("Fallback regex parsing did not find any matches.")
    except Exception as ex:
        log.error(f"Fallback regex parsing failed: {ex}")

    return []


def fetch_table_with_description(manifest: "Manifest") -> pd.DataFrame:
    """
    Fetches all table details from the manifest.
    """
    table_data = []
    for source in manifest.sources.values():
        table = source.table
        if not table:
            continue

        table_data.append(
            {
                "table_name": table.name,
                "table_description": table.description or "",
                "domain_name": source.schema,  # Using schema as domain for now
            }
        )

    if not table_data:
        return pd.DataFrame(columns=["table_name", "table_description", "domain_name"])

    return pd.DataFrame(table_data)


def fetch_column_with_description(manifest: "Manifest") -> pd.DataFrame:
    """
    Fetches all column details from the manifest.
    """
    column_data = []
    for source in manifest.sources.values():
        table = source.table
        if not table or not table.columns:
            continue

        for column in table.columns:
            column_data.append(
                {
                    "id": f"{table.name}.{column.name}",
                    "table_name": table.name,
                    "column_name": column.name,
                    "business_glossary": column.description or "",
                    "business_tags": column.tags or [],
                    "db_schema": source.schema,
                }
            )

    if not column_data:
        return pd.DataFrame(
            columns=[
                "id",
                "table_name",
                "column_name",
                "business_glossary",
                "business_tags",
                "db_schema",
            ]
        )

    return pd.DataFrame(column_data)
