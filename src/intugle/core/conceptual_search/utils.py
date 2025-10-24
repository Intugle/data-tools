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
        # Try to parse a clean JSON array of strings
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
        # Attempt to extract a list manually from the raw text
        matches = re.findall(r"\[(.*?)\]", raw_text, re.DOTALL)
        if matches:
            items = re.findall(r'"([^"]+)"', matches[0])
            return items
        else:
            log.info("Fallback regex parsing did not find any matches.")
    except Exception as ex:
        log.error(f"Fallback regex parsing didnot find any matches\nReason: {ex}")

    return []


def extract_concepts_column(text, llm):
    """
    Extract key concepts from text using GROQ's API.

    Args:
        text (str): Text to extract concepts from

    Returns:
        List[str]: List of key concepts or entities
    """
    system_message = """
    # Instructions:
    - Extract key concepts and entities from the provided description of a field in database .
    - Return ONLY a list of 2 key terms, entities, or concepts that are most important in this text.
    - Return a valid JSON array of strings. Example:["Entity1", "Entity2"]
    - Donot mention table names or field name itself, or irrelevant terms , irrelevant entities or irreleavant concepts.
    - The list of terms should be unique.
    """

    messages = [
        ("system", system_message),
        ("user", f"Extract key concepts from field description:\n\n{text[:3000]}"),
    ]
    try:
        ai_msg = llm.invoke(messages)
        concepts = manual_concept_extraction(ai_msg)
        return concepts
    except Exception as fallback_err:
        log.info(f"Fallback parsing also failed: {fallback_err}")

    return []


def fetch_column_with_description(manifest: "Manifest") -> pd.DataFrame:
    """
    Fetches all column details from the manifest.
    This replaces the original SQL-based implementation.
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