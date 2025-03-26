"""FAISS vector store integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class FAISSVectorStore:
    """Wrapper for Langchain's FAISS vector store."""
    
    def __init__(
        self,
        embedding_function: Embeddings,
        index: Any = None,
        docstore: Any = None,
        index_to_docstore_id: Optional[Dict[int, str]] = None,
    ):
        """Initialize the FAISSVectorStore.
        
        Args:
            embedding_function: Embedding function to use
            index: Optional FAISS index
            docstore: Optional document store
            index_to_docstore_id: Optional mapping from index to document store ID
        """
        self.embedding_function = embedding_function
        
        # Initialize the vector store if all components are provided
        if index is not None and docstore is not None and index_to_docstore_id is not None:
            self.vector_store = FAISS(
                embedding_function=embedding_function,
                index=index,
                docstore=docstore,
                index_to_docstore_id=index_to_docstore_id,
            )
        else:
            # Create an empty vector store
            self.vector_store = FAISS.from_texts(
                texts=["placeholder"],
                embedding=embedding_function,
            )
            # Remove the placeholder
            self.vector_store.delete(["placeholder"])
    
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
    
    def save_local(self, folder_path: str, index_name: str = "index") -> None:
        """Save the vector store to disk.
        
        Args:
            folder_path: Path to save the vector store
            index_name: Name of the index file
        """
        self.vector_store.save_local(folder_path, index_name)
    
    @classmethod
    def load_local(
        cls,
        folder_path: str,
        embedding_function: Embeddings,
        index_name: str = "index",
        allow_dangerous_deserialization: bool = False,
    ) -> "FAISSVectorStore":
        """Load a vector store from disk.
        
        Args:
            folder_path: Path to load the vector store from
            embedding_function: Embedding function to use
            index_name: Name of the index file
            allow_dangerous_deserialization: Whether to allow dangerous deserialization
            
        Returns:
            FAISSVectorStore instance
        """
        vector_store = FAISS.load_local(
            folder_path=folder_path,
            embeddings=embedding_function,
            index_name=index_name,
            allow_dangerous_deserialization=allow_dangerous_deserialization,
        )
        
        instance = cls(embedding_function=embedding_function)
        instance.vector_store = vector_store
        return instance
    
    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding_function: Embeddings,
    ) -> "FAISSVectorStore":
        """Create a vector store from documents.
        
        Args:
            documents: List of documents
            embedding_function: Embedding function to use
            
        Returns:
            FAISSVectorStore instance
        """
        vector_store = FAISS.from_documents(
            documents=documents,
            embedding=embedding_function,
        )
        
        instance = cls(embedding_function=embedding_function)
        instance.vector_store = vector_store
        return instance
    
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_function: Embeddings,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> "FAISSVectorStore":
        """Create a vector store from texts.
        
        Args:
            texts: List of texts
            embedding_function: Embedding function to use
            metadatas: Optional list of metadata dictionaries
            
        Returns:
            FAISSVectorStore instance
        """
        vector_store = FAISS.from_texts(
            texts=texts,
            embedding=embedding_function,
            metadatas=metadatas,
        )
        
        instance = cls(embedding_function=embedding_function)
        instance.vector_store = vector_store
        return instance