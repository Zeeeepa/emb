"""Chroma vector store integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class ChromaVectorStore:
    """Wrapper for Langchain's Chroma vector store."""
    
    def __init__(
        self,
        embedding_function: Embeddings,
        persist_directory: Optional[str] = None,
        collection_name: str = "default_collection",
        collection_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the ChromaVectorStore.
        
        Args:
            embedding_function: Embedding function to use
            persist_directory: Optional directory to persist the vector store
            collection_name: Name of the collection
            collection_metadata: Optional metadata for the collection
        """
        self.embedding_function = embedding_function
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.collection_metadata = collection_metadata or {}
        
        # Initialize the vector store
        self.vector_store = Chroma(
            embedding_function=embedding_function,
            persist_directory=persist_directory,
            collection_name=collection_name,
            collection_metadata=self.collection_metadata,
        )
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store.
        
        Args:
            documents: List of documents to add
            
        Returns:
            List of document IDs
        """
        return self.vector_store.add_documents(documents)
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Add texts to the vector store.
        
        Args:
            texts: List of texts to add
            metadatas: Optional list of metadata dictionaries
            
        Returns:
            List of document IDs
        """
        return self.vector_store.add_texts(texts, metadatas=metadatas)
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Document]:
        """Search for similar documents.
        
        Args:
            query: Query string
            k: Number of results to return
            filter: Optional filter to apply
            
        Returns:
            List of similar documents
        """
        return self.vector_store.similarity_search(query, k=k, filter=filter, **kwargs)
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[tuple[Document, float]]:
        """Search for similar documents and return scores.
        
        Args:
            query: Query string
            k: Number of results to return
            filter: Optional filter to apply
            
        Returns:
            List of (document, score) tuples
        """
        return self.vector_store.similarity_search_with_score(query, k=k, filter=filter, **kwargs)
    
    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Document]:
        """Search for documents using maximal marginal relevance.
        
        Args:
            query: Query string
            k: Number of results to return
            fetch_k: Number of results to fetch before filtering
            lambda_mult: Diversity parameter (0 = max diversity, 1 = max relevance)
            filter: Optional filter to apply
            
        Returns:
            List of documents
        """
        return self.vector_store.max_marginal_relevance_search(
            query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult, filter=filter, **kwargs
        )
    
    def persist(self) -> None:
        """Persist the vector store to disk."""
        if self.persist_directory:
            self.vector_store.persist()
        else:
            raise ValueError("Cannot persist without a persist_directory")
    
    def delete(self, ids: List[str]) -> Optional[bool]:
        """Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            True if successful, False otherwise
        """
        return self.vector_store.delete(ids)
    
    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding_function: Embeddings,
        persist_directory: Optional[str] = None,
        collection_name: str = "default_collection",
        collection_metadata: Optional[Dict[str, Any]] = None,
    ) -> "ChromaVectorStore":
        """Create a vector store from documents.
        
        Args:
            documents: List of documents
            embedding_function: Embedding function to use
            persist_directory: Optional directory to persist the vector store
            collection_name: Name of the collection
            collection_metadata: Optional metadata for the collection
            
        Returns:
            ChromaVectorStore instance
        """
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embedding_function,
            persist_directory=persist_directory,
            collection_name=collection_name,
            collection_metadata=collection_metadata or {},
        )
        
        instance = cls(
            embedding_function=embedding_function,
            persist_directory=persist_directory,
            collection_name=collection_name,
            collection_metadata=collection_metadata,
        )
        instance.vector_store = vector_store
        return instance
    
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_function: Embeddings,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        persist_directory: Optional[str] = None,
        collection_name: str = "default_collection",
        collection_metadata: Optional[Dict[str, Any]] = None,
    ) -> "ChromaVectorStore":
        """Create a vector store from texts.
        
        Args:
            texts: List of texts
            embedding_function: Embedding function to use
            metadatas: Optional list of metadata dictionaries
            persist_directory: Optional directory to persist the vector store
            collection_name: Name of the collection
            collection_metadata: Optional metadata for the collection
            
        Returns:
            ChromaVectorStore instance
        """
        vector_store = Chroma.from_texts(
            texts=texts,
            embedding=embedding_function,
            metadatas=metadatas,
            persist_directory=persist_directory,
            collection_name=collection_name,
            collection_metadata=collection_metadata or {},
        )
        
        instance = cls(
            embedding_function=embedding_function,
            persist_directory=persist_directory,
            collection_name=collection_name,
            collection_metadata=collection_metadata,
        )
        instance.vector_store = vector_store
        return instance