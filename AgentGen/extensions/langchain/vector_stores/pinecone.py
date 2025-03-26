"""Pinecone vector store integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable, Tuple
import os
from uuid import uuid4

from langchain_community.vectorstores import Pinecone
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class PineconeVectorStore:
    """Wrapper for Langchain's Pinecone vector store."""
    
    def __init__(
        self,
        embedding_function: Embeddings,
        index_name: str,
        namespace: Optional[str] = None,
        text_key: str = "text",
        embedding_key: str = "embedding",
    ):
        """Initialize the PineconeVectorStore.
        
        Args:
            embedding_function: Embedding function to use
            index_name: Name of the Pinecone index
            namespace: Optional namespace to use
            text_key: Key to use for text in the Pinecone index
            embedding_key: Key to use for embeddings in the Pinecone index
        """
        self.embedding_function = embedding_function
        self.index_name = index_name
        self.namespace = namespace
        self.text_key = text_key
        self.embedding_key = embedding_key
        
        # Initialize the vector store
        self.vector_store = Pinecone(
            embedding=embedding_function,
            index_name=index_name,
            namespace=namespace,
            text_key=text_key,
        )
    
    def add_documents(self, documents: List[Document], ids: Optional[List[str]] = None) -> List[str]:
        """Add documents to the vector store.
        
        Args:
            documents: List of documents to add
            ids: Optional list of IDs to use
            
        Returns:
            List of document IDs
        """
        if ids is None:
            ids = [str(uuid4()) for _ in range(len(documents))]
        return self.vector_store.add_documents(documents, ids=ids)
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[str]:
        """Add texts to the vector store.
        
        Args:
            texts: List of texts to add
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of IDs to use
            
        Returns:
            List of document IDs
        """
        if ids is None:
            ids = [str(uuid4()) for _ in range(len(texts))]
        return self.vector_store.add_texts(texts, metadatas=metadatas, ids=ids, **kwargs)
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        **kwargs
    ) -> List[Document]:
        """Search for similar documents.
        
        Args:
            query: Query string
            k: Number of results to return
            filter: Optional filter to apply
            namespace: Optional namespace to search in (overrides the instance namespace)
            
        Returns:
            List of similar documents
        """
        return self.vector_store.similarity_search(
            query, k=k, filter=filter, namespace=namespace or self.namespace, **kwargs
        )
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        **kwargs
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents and return scores.
        
        Args:
            query: Query string
            k: Number of results to return
            filter: Optional filter to apply
            namespace: Optional namespace to search in (overrides the instance namespace)
            
        Returns:
            List of (document, score) tuples
        """
        return self.vector_store.similarity_search_with_score(
            query, k=k, filter=filter, namespace=namespace or self.namespace, **kwargs
        )
    
    def delete(self, ids: List[str], namespace: Optional[str] = None) -> None:
        """Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete
            namespace: Optional namespace to delete from (overrides the instance namespace)
        """
        self.vector_store.delete(ids=ids, namespace=namespace or self.namespace)
    
    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding_function: Embeddings,
        index_name: str,
        namespace: Optional[str] = None,
        text_key: str = "text",
        ids: Optional[List[str]] = None,
    ) -> "PineconeVectorStore":
        """Create a vector store from documents.
        
        Args:
            documents: List of documents
            embedding_function: Embedding function to use
            index_name: Name of the Pinecone index
            namespace: Optional namespace to use
            text_key: Key to use for text in the Pinecone index
            ids: Optional list of IDs to use
            
        Returns:
            PineconeVectorStore instance
        """
        if ids is None:
            ids = [str(uuid4()) for _ in range(len(documents))]
            
        vector_store = Pinecone.from_documents(
            documents=documents,
            embedding=embedding_function,
            index_name=index_name,
            namespace=namespace,
            text_key=text_key,
            ids=ids,
        )
        
        instance = cls(
            embedding_function=embedding_function,
            index_name=index_name,
            namespace=namespace,
            text_key=text_key,
        )
        instance.vector_store = vector_store
        return instance
    
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_function: Embeddings,
        index_name: str,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        namespace: Optional[str] = None,
        text_key: str = "text",
        ids: Optional[List[str]] = None,
    ) -> "PineconeVectorStore":
        """Create a vector store from texts.
        
        Args:
            texts: List of texts
            embedding_function: Embedding function to use
            index_name: Name of the Pinecone index
            metadatas: Optional list of metadata dictionaries
            namespace: Optional namespace to use
            text_key: Key to use for text in the Pinecone index
            ids: Optional list of IDs to use
            
        Returns:
            PineconeVectorStore instance
        """
        if ids is None:
            ids = [str(uuid4()) for _ in range(len(texts))]
            
        vector_store = Pinecone.from_texts(
            texts=texts,
            embedding=embedding_function,
            index_name=index_name,
            metadatas=metadatas,
            namespace=namespace,
            text_key=text_key,
            ids=ids,
        )
        
        instance = cls(
            embedding_function=embedding_function,
            index_name=index_name,
            namespace=namespace,
            text_key=text_key,
        )
        instance.vector_store = vector_store
        return instance