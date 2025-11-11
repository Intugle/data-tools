import ast
import logging
import os

from itertools import chain
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from qdrant_client import models
from tqdm import tqdm

from intugle.core import settings
from intugle.core.conceptual_search.models import QdrantCollectionSuffix
from intugle.core.conceptual_search.utils import (
    batched,
    fetch_table_with_description,
    manual_concept_extraction,
)
from intugle.core.llms.chat import ChatModelLLM
from intugle.core.llms.embeddings import Embeddings, EmbeddingsType
from intugle.core.vector_store import AsyncQdrantService, VDocument
from intugle.core.vector_store.qdrant import QdrantVectorConfiguration

log = logging.getLogger(__name__)

tqdm.pandas()


def conceptual_search_collection_name():
    return f"{settings.PROJECT_ID}_conceptual_search_tables"


CONCEPTUAL_SEARCH_COLLECTION_NAME = conceptual_search_collection_name()


def collection_name(prefix: str, suffix: str = QdrantCollectionSuffix.TABLE):

    return f"{prefix}{suffix}"


async def fetch_embeddings_from_qdrant(collection_name):
     
    data = pd.DataFrame()

    async with AsyncQdrantService(collection_name=collection_name, collection_configurations={}) as qdb:

        data = await qdb.get(includes=["metadata", "embeddings"], return_document=False)

        data = pd.DataFrame([d.model_dump() for d in data])[["payload", "vector"]]
        
    if data.shape[0] > 0:

        data = pd.concat(
                [data, pd.json_normalize(data.payload)], axis=1
            )[["row", "source", "vector", "content"]]

        if "row" in data.columns:
            
            return data.sort_values(by="row", ascending=True).reset_index(drop=True)
    
    return data


async def create_embeddings(doc: list[VDocument], recreate: bool = False):
    """
    Create and store embeddings for the given documents using the configured embedding model.
    This function aligns with the intugle architecture for handling embeddings and vector stores.
    """
    embedding_model = Embeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        tokenizer_model=settings.TOKENIZER_MODEL_NAME,
    )

    vectors_config = {
        f"{embedding_model.model_name}-{EmbeddingsType.LATE}": models.VectorParams(
            size=embedding_model.embeddings_size,
            distance=models.Distance.COSINE,
            multivector_config=models.MultiVectorConfig(
                comparator=models.MultiVectorComparator.MAX_SIM
            ),
        ),
    }
    configuration = QdrantVectorConfiguration(vectors_config=vectors_config)

    async with AsyncQdrantService(
        collection_name=CONCEPTUAL_SEARCH_COLLECTION_NAME,
        collection_configurations=configuration,
    ) as qdb:
        if recreate:
            await qdb.delete_collection()
            await qdb.create_collection()
            log.info(f"[*] Deleted and recreated collection {CONCEPTUAL_SEARCH_COLLECTION_NAME}")

        count_result = await qdb.count()
        count_req = count_result.count
        if count_req < len(doc):
            log.info("Vectorizing and adding documents to Qdrant...")
            vectors = await embedding_model.aencode(
                [d.page_content for d in doc],
                embeddings_types=[EmbeddingsType.LATE],
            )
            late_vectors = vectors[EmbeddingsType.LATE]

            points = []
            for i, document in enumerate(doc):
                point_id = str(uuid4())
                vector = {f"{embedding_model.model_name}-{EmbeddingsType.LATE}": late_vectors[i]}
                payload = {**document.metadata, "content": document.page_content}
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )

            for batch in batched(points, 30):
                qdb.bulk_insert(points=batch)
            log.info("Embeddings created and inserted into Qdrant DB")

    log.info("Fetching embeddings from Qdrant...")
    all_vector_records = await fetch_embeddings_from_qdrant(
        collection_name=CONCEPTUAL_SEARCH_COLLECTION_NAME
    )
    log.info("Embeddings fetched from Qdrant.")

    vector_name = f"{embedding_model.model_name}-{EmbeddingsType.LATE}"
    all_embeddings = [
        np.array(item["vector"][vector_name])
        for _, item in all_vector_records.iterrows()
    ]

    return all_embeddings


def filter_out_concepts(data: pd.DataFrame, threshold: float = 0.1):
    total_documents = data.shape[0]
    concepts = pd.DataFrame(list(chain(*data.concepts.tolist())), columns=["concepts"])
    value_counts = concepts.value_counts().reset_index()
    value_counts["proportion"] = value_counts["count"] / total_documents

    return value_counts.loc[value_counts.proportion > threshold].concepts.tolist()


def clean_concepts(concepts: list):

    if isinstance(concepts, list):
        
        return list(map(lambda concept: concept.strip().lower(), concepts))
    
    return concepts


def remove_unwanted_concepts(concepts: list, filter_out: list):

    return list(filter(lambda concept: concept not in filter_out, concepts))


def extract_concepts_table(text, llm):
    """
    Extract key concepts from a table description.
    """
    system_message = """
    # Instructions:
    - Extract key concepts and entities from the provided description of a database table.
    - Return ONLY a list of 1-5 key terms, entities, or concepts that are most important in this text.
    - Return a valid JSON array of strings. Example:["Entity1", "Entity2"]
    - Do not mention table names or irrelevant terms.
    - The list of terms should be unique.
    """
    messages = [
        ("system", system_message),
        ("user", f"Extract key concepts from table description:\n\n{text[:3000]}"),
    ]
    try:
        ai_msg = llm.invoke(messages)
        return manual_concept_extraction(ai_msg)
    except Exception as e:
        log.error(f"Concept extraction for table failed: {e}")
    return []


def prepare_chunk_document(manifest):
    table_description_path = os.path.join(settings.DESCRIPTIONS_DIR, "table_description.csv")
    table_description_path = Path(table_description_path)
    table_description_path.parent.mkdir(exist_ok=True, parents=True)

    llm = ChatModelLLM.get_llm(
                model_name=settings.LLM_PROVIDER,
                llm_config={"temperature": 0.05},
            )
    if not table_description_path.exists():

        table_description_df = fetch_table_with_description(manifest)

        def build_table_description(row: pd.Series):
            
            description = []
        
            description += [f"Table Name: {row['table_name']}", f"Table Description: {row['table_description']}"]
        
            return "\n".join(description)
    
        table_description_df['table_description'] = table_description_df.apply(build_table_description, axis=1)
        table_description_df['id'] = table_description_df['table_name']
    
        log.info("[*] Extracting concepts for tables")
        
        for i, data in tqdm(enumerate(list(batched(table_description_df, 30)), 1)):

            concepts = data["table_description"].apply(extract_concepts_table, llm=llm)
            
            table_description_df.loc[data.index, "concepts"] = concepts
            
            log.info(f"[*] Batch {i} completed")

        table_description_df["concepts"] = table_description_df.concepts.apply(clean_concepts)

        table_description_df.to_csv(table_description_path, index=False)

    else:

        table_description_df = pd.read_csv(table_description_path)

        table_description_df["concepts"] = table_description_df.concepts.apply(ast.literal_eval)

        def remove_concepts(concepts: list, to_remove=["hvac industry"]):

            return list(filter(lambda concept: concept.strip().lower() not in to_remove, concepts))
        
        table_description_df["concepts"] = table_description_df.concepts.apply(remove_concepts)

    data_documents = []

    for index, row in table_description_df.iterrows():
        
        data_documents.append(VDocument(page_content=row['table_description'].strip().lower(), metadata={"source": row['id'], "row": index, "concepts": row['concepts']}))
    
    return data_documents