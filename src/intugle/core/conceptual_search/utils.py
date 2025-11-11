import json
import logging
import os
import re

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from intugle.parser.manifest import Manifest

log = logging.getLogger(__name__)


def clean_query(s: str) -> str:
    s = s.lower()
    s = ' '.join(s.split())
    return s


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
            }
        )

    if not table_data:
        return pd.DataFrame(columns=["table_name", "table_description"])

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


def extract_data_product_info(documents):
    extracted_info = []

    if not documents:
        print("No documents found.")
        return extracted_info  # Return empty list if no documents are present

    for doc in documents:
        data_product_name = None
        dimensions = []
        measures = []

        # Extracting Data Product Name from page_content
        # if "Data_Product:" in doc.page_content:
        data_product_name = doc.page_content.split("Data_Product:")[-1].strip()

        # Extracting Dimensions and Measures from metadata
        dimensions = doc.metadata.get("Dimensions", "").split(", ")
        measures = doc.metadata.get("Measures", "").split(", ")

        # Append extracted information as a dictionary
        extracted_info.append(
            {
                "Data_Product": data_product_name,
                "Dimensions": dimensions,
                "Measures": measures,
            }
        )

    return extracted_info


def extract_table_details(documents):
    extracted_info = []
    if not documents:
        print("No tables found.")
        return extracted_info  # Return empty list if no documents are present

    for doc in documents:
        # Extracting table details
        table_details = doc.page_content.strip("text: ")

        # Append extracted information as a dictionary
        extracted_info.append({doc.metadata["table"]: table_details})

    return extracted_info


def langfuse_callback_handler():
    try:
        from langfuse.callback import CallbackHandler
    except ImportError:
        log.warning(
            "[!] langfuse package not installed. Please install it to use langfuse callback handler."
        )
        return None
    
    langfuse_handler = CallbackHandler(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ["LANGFUSE_HOST"],
        environment=os.environ.get("LANGFUSE_ENVIRONMENT_NAME", "dev"),
        # trace_name=trace_name,
        # session_id=session_id,
        # tags=tags
    )

    # Check for langfuse handler then only add it to the callback
    try:
        langfuse_handler.auth_check()
        return langfuse_handler
    except Exception as ex:
        log.warning(f"[!] Could not connect to langfuse: {str(ex)}")
        return None
