"""Contextual compression retriever integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun


class ContextualCompressionRetriever(BaseRetriever):
    """Wrapper for Langchain's contextual compression retriever."""
    
    def __init__(
        self,
        base_retriever: BaseRetriever,
        base_compressor: Any,
    ):
        """Initialize the ContextualCompressionRetriever.
        
        Args:
            base_retriever: Base retriever to use
            base_compressor: Document compressor to use
        """
        super().__init__()
        self.base_retriever = base_retriever
        self.base_compressor = base_compressor
    
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
        # Get documents from base retriever
        docs = self.base_retriever.get_relevant_documents(query, callbacks=run_manager.get_child())
        
        # Compress documents
        compressed_docs = self.base_compressor.compress_documents(docs, query)
        
        return compressed_docs
    
    @classmethod
    def from_llm(
        cls,
        base_retriever: BaseRetriever,
        llm: Any,
        chain_type: str = "stuff",
        verbose: bool = False,
    ) -> "ContextualCompressionRetriever":
        """Create a retriever with LLM-based document compression.
        
        Args:
            base_retriever: Base retriever to use
            llm: Language model to use for compression
            chain_type: Type of chain to use for compression
            verbose: Whether to print verbose output
            
        Returns:
            ContextualCompressionRetriever instance
        """
        from langchain.retrievers.document_compressors import LLMChainExtractor
        
        compressor = LLMChainExtractor.from_llm(llm, chain_type=chain_type, verbose=verbose)
        
        return cls(
            base_retriever=base_retriever,
            base_compressor=compressor,
        )