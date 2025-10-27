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
    fetch_column_with_description,
    manual_concept_extraction,
)
from intugle.core.llms.chat import ChatModelLLM
from intugle.core.llms.embeddings import Embeddings, EmbeddingsType
from intugle.core.vector_store import AsyncQdrantService, VDocument
from intugle.core.vector_store.qdrant import QdrantVectorConfiguration

log = logging.getLogger(__name__)

tqdm.pandas()


def conceptual_search_collection_name():
    return f"{settings.PROJECT_ID}_conceptual_search_columns"


CONCEPTUAL_SEARCH_COLLECTION_NAME = conceptual_search_collection_name()


def collection_name(prefix: str, suffix: str = QdrantCollectionSuffix.FIELD):

    return f"{prefix}{suffix}"


async def fetch_embeddings_from_qdrant(collection_name):
     
    data = pd.DataFrame()

    async with AsyncQdrantService(collection_name=collection_name, collection_configurations={}) as qdb:

        data = await qdb.get(includes=["metadata", "embeddings"], return_document=False)

        data = pd.DataFrame([d.model_dump() for d in data])[["payload", "vector"]]
        
    if data.shape[0] > 0:

        data = pd.concat(
                [data, pd.json_normalize(data.payload)], axis=1
            )[["row", "source", "vector", "content"]]  # [["row", "source", "concepts","vector","content"]]

        if "row" in data.columns:
            
            return data.sort_values(by="row", ascending=True).reset_index(drop=True)
    
    return data


async def create_embeddings(doc: list[VDocument], recreate: bool = False):
    """
    Create and store embeddings for the given documents using the configured embedding model.
    This function aligns with the intugle architecture for handling embeddings and vector stores.
    """
    # 1. Initialize the standard Embeddings class from project settings
    embedding_model = Embeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        tokenizer_model=settings.TOKENIZER_MODEL_NAME,
    )

    # 2. Create the vector store configuration programmatically
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

    # 3. Instantiate the AsyncQdrantService
    async with AsyncQdrantService(
        collection_name=CONCEPTUAL_SEARCH_COLLECTION_NAME,
        collection_configurations=configuration,
    ) as qdb:
        if recreate:
            await qdb.delete_collection()
            await qdb.create_collection()
            log.info(f"[*] Deleted and recreated collection {CONCEPTUAL_SEARCH_COLLECTION_NAME}")

        # 4. Check if documents need to be vectorized and inserted
        count_result = await qdb.count()
        count_req = count_result.count
        if count_req < len(doc):
            log.info("Vectorizing and adding documents to Qdrant...")
            # 5. Vectorize documents
            vectors = await embedding_model.aencode(
                [d.page_content for d in doc],
                embeddings_types=[EmbeddingsType.LATE],
            )
            late_vectors = vectors[EmbeddingsType.LATE]

            # 6. Create PointStruct objects for insertion
            points = []
            for i, document in enumerate(doc):
                point_id = str(uuid4())
                vector = {f"{embedding_model.model_name}-{EmbeddingsType.LATE}": late_vectors[i]}
                # Merge metadata and page_content into the payload
                payload = {**document.metadata, "content": document.page_content}
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )

            # 7. Bulk insert into Qdrant
            for batch in batched(points, 30):
                qdb.bulk_insert(points=batch)
            log.info("Embeddings created and inserted into Qdrant DB")

    # 8. Fetch and return the embeddings
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


def extract_concepts_column(text, llm):
    """
    Extract key concepts from a column description.
    """
    system_message = """
    # Instructions:
    - Extract key concepts and entities from the provided description of a field in a database.
    - Return ONLY a list of 2 key terms, entities, or concepts that are most important in this text.
    - Return a valid JSON array of strings. Example:["Entity1", "Entity2"]
    - Do not mention table names or the field name itself, or irrelevant terms.
    - The list of terms should be unique.
    """

    messages = [
        ("system", system_message),
        ("user", f"Extract key concepts from field description:\n\n{text[:3000]}"),
    ]
    try:
        ai_msg = llm.invoke(messages)
        return manual_concept_extraction(ai_msg)
    except Exception as e:
        log.error(f"Concept extraction for column failed: {e}")
    return []


def prepare_chunk_document(manifest):
    column_description_path = os.path.join(settings.DESCRIPTIONS_DIR, "column_description.csv")
    column_description_path = Path(column_description_path)
    column_description_path.parent.mkdir(exist_ok=True, parents=True)

    llm = ChatModelLLM.get_llm(
                model_name=settings.LLM_PROVIDER,
                llm_config={"temperature": 0.05},
            )
    if not column_description_path.exists():

        column_description_df = fetch_column_with_description(manifest)

        column_description_df['Text'] = column_description_df['column_name'] + " - " + column_description_df['business_glossary']

        column_description_df['id'] = column_description_df['table_name'] + "$$##$$" + column_description_df['column_name']

        column_description_df = column_description_df[(column_description_df["business_glossary"] != "")].reset_index(drop=True)

        log.info(f"[*] Extracting concepts for {column_description_df.shape[0]} columns")

        for i, data in tqdm(enumerate(batched(column_description_df, 30), 1), position=0, leave=True):
        
            column_description_df.loc[data.index, "concepts"] = data["Text"].progress_apply(lambda text: clean_concepts(extract_concepts_column(text=text, llm=llm)))
            
            column_description_df.loc[data.index, "concepts"] = column_description_df.loc[data.index].apply(lambda row: remove_unwanted_concepts(concepts=row["concepts"], filter_out=[row['column_name'], 'sap erp', 'sap erp system', 'sap']), axis=1)
            
            column_description_df.loc[data.index].to_csv(column_description_path,
                                                         index=False,
                                                         mode='a',
                                                         header=not os.path.exists(column_description_path))

            log.info(f"[*] Batch {i} completed")

    else:
                   
        column_description_df = pd.read_csv(column_description_path)

        column_description_df["concepts"] = column_description_df.concepts.apply(ast.literal_eval)

    concepts_to_be_removed = filter_out_concepts(data=column_description_df[["concepts"]])
    
    column_description_df["concepts"] = column_description_df.apply(lambda row: remove_unwanted_concepts(concepts=row["concepts"], filter_out=concepts_to_be_removed), axis=1)

    data_documents = []

    for index, row in column_description_df.iterrows():
        
        data_documents.append(VDocument(page_content=row['Text'].strip().lower(), metadata={"source": row['id'], "row": index, "concepts": row['concepts']}))

    return data_documents
