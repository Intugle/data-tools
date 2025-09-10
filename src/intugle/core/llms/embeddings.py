import asyncio

from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Callable, Dict, List, Optional

import tiktoken

from langchain.embeddings.base import init_embeddings


class EmbeddingsType(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    LATE = "late"


ListEmbeddingsType = List[EmbeddingsType]
Documents = List[str]


class Embeddings:
    def __init__(
        self,
        model_name: str,
        tokenizer_model: str,
        config: dict = {},
        executor: Optional[ThreadPoolExecutor] = None,
        max_workers: int = 30,
        embeddings_size: Optional[int] = None,
    ):
        self.model_name = model_name
        self.model = init_embeddings(model_name, **config)
        self._embed_func: Dict[EmbeddingsType, Callable] = {
            EmbeddingsType.DENSE: self.dense,
            EmbeddingsType.SPARSE: self.sparse,
            EmbeddingsType.LATE: self.late,
        }
        self._aembed_func: Dict[EmbeddingsType, Callable] = {
            EmbeddingsType.DENSE: self.adense,
            EmbeddingsType.SPARSE: self.asparse,
            EmbeddingsType.LATE: self.alate,
        }
        self.max_workers = max_workers
        self._executor = executor
        self.tokenizer = tiktoken.get_encoding(tokenizer_model)
        self._embeddings_size = embeddings_size
    
    @property
    def embeddings_size(self):
        if self._embeddings_size is None:
            self._embeddings_size = len(self.model.embed_query("test"))
        return self._embeddings_size

    @property
    def executor(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    def dense(self, documents: Documents):
        embeddings = self.model.embed_documents(documents)
        return embeddings

    def _tokenize_and_encode(self, query: str):
        """
        Convert query to tokens and embed them
        Args:
            query (str): String to be tokenized and embedded
        Returns:
            _type_: _description_
        """
        token_ids = self.tokenizer.encode(query)
        tokens = [self.tokenizer.decode([token_id]) for token_id in token_ids]
        late_embeddings = self.dense(tokens)
        return late_embeddings

    def late(self, documents: Documents):
        documents_list = [documents] if isinstance(documents, str) else documents
        late_embeddings = []
        for i in documents_list:
            embedding = self._tokenize_and_encode(i)
            late_embeddings.append(embedding)
        return late_embeddings[0] if isinstance(documents, str) else late_embeddings

    def sparse(self, documents: Documents):
        raise NotImplementedError("Sparse Embeddings yet to implement")

    def encode(self, documents: Documents, embeddings_types: ListEmbeddingsType):
        response = {}
        for embeddings_type in embeddings_types:
            embed_func = self._embed_func[embeddings_type]
            response[embeddings_type] = embed_func(documents)
        return response

    async def adense(self, documents: Documents):
        embeddings = await self.model.aembed_documents(documents)
        return embeddings

    async def _atokenize_and_encode(self, query: str):
        """
        Convert query to tokens and embed them
        Args:
            query (str): String to be tokenized and embedded
        Returns:
            _type_: _description_
        """

        # Using synchrounous code in async
        def tokenize(query):
            token_ids = self.tokenizer.encode(query)
            tokens = [self.tokenizer.decode([token_id]) for token_id in token_ids]
            return tokens

        loop = asyncio.get_running_loop()
        tokens = await loop.run_in_executor(self.executor, tokenize, query)

        late_embeddings = await self.adense(tokens)
        return late_embeddings

    async def alate(self, documents: Documents):
        documents_list = [documents] if isinstance(documents, str) else documents
        late_embeddings = []
        for i in documents_list:
            embedding = await self._atokenize_and_encode(i)
            late_embeddings.append(embedding)
        return late_embeddings[0] if isinstance(documents, str) else late_embeddings

    async def asparse(self, documents: Documents):
        raise NotImplementedError("Sparse Embeddings yet to implement for AzureOpenAIEmbeddings")

    async def aencode(self, documents: Documents, embeddings_types: ListEmbeddingsType):
        response = {}
        try:
            for embeddings_type in embeddings_types:
                aembed_func = self._aembed_func[embeddings_type]
                response[embeddings_type] = await aembed_func(documents)
            return response
        except Exception as e:
            print("Error: ", e)
            import traceback
            print(traceback.format_exc())
