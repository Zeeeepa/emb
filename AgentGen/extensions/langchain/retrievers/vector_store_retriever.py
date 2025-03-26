"""Vector store retriever integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os
from enum import Enum

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun


class SearchType(str, Enum):
    """Search types for vector store retriever."""
    
    SIMILARITY = "similarity"
    MMR = "mmr"


class VectorStoreRetriever(BaseRetriever):
    """Wrapper for Langchain's vector store retriever."""
    
    def __init__(
        self,
        vector_store: Any,
        search_type: str = "similarity",
        search_kwargs: Optional[Dict[str, Any]] = None,
        k: int = 4,
    ):
        """Initialize the VectorStoreRetriever.
        
        Args:
            vector_store: Vector store to use
            search_type: Type of search to perform (similarity or mmr)
            search_kwargs: Optional search arguments
            k: Number of documents to retrieve
        """
        super().__init__()
        self.vector_store = vector_store
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {}
        self.k = k
        
        # Set default k in search_kwargs if not provided
        if "k" not in self.search_kwargs:
            self.search_kwargs["k"] = self.k
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Get documents relevant to the query.
        
        Args:
            query: Query string
            run_manager: Callback manager
            
        Returns:
            List of relevant documents
        """
        if self.search_type == SearchType.SIMILARITY:
            docs = self.vector_store.similarity_search(query, **self.search_kwargs)
        elif self.search_type == SearchType.MMR:
            docs = self.vector_store.max_marginal_relevance_search(query, **self.search_kwargs)
        else:
            raise ValueError(f"Search type {self.search_type} not supported")
        
        return docs
    
    @classmethod
    def from_vector_store(
        cls,
        vector_store: Any,
        search_type: str = "similarity",
        search_kwargs: Optional[Dict[str, Any]] = None,
        k: int = 4,
    ) -> "VectorStoreRetriever":
        """Create a retriever from a vector store.
        
        Args:
            vector_store: Vector store to use
            search_type: Type of search to perform (similarity or mmr)
            search_kwargs: Optional search arguments
            k: Number of documents to retrieve
            
        Returns:
            VectorStoreRetriever instance
        """
        return cls(
            vector_store=vector_store,
            search_type=search_type,
            search_kwargs=search_kwargs,
            k=k,
        )