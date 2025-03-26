"""Self-query retriever integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable, Type
import os

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.language_models import BaseLanguageModel


class SelfQueryRetriever(BaseRetriever):
    """Wrapper for Langchain's self-query retriever."""
    
    def __init__(
        self,
        vectorstore: Any,
        llm: BaseLanguageModel,
        document_contents: str,
        metadata_field_info: List[Dict[str, Any]],
        structured_query_translator: Optional[Any] = None,
        verbose: bool = False,
    ):
        """Initialize the SelfQueryRetriever.
        
        Args:
            vectorstore: Vector store to use
            llm: Language model to use for generating queries
            document_contents: Description of the document contents
            metadata_field_info: Information about metadata fields
            structured_query_translator: Optional translator for structured queries
            verbose: Whether to print verbose output
        """
        super().__init__()
        self.vectorstore = vectorstore
        self.llm = llm
        self.document_contents = document_contents
        self.metadata_field_info = metadata_field_info
        self.structured_query_translator = structured_query_translator
        self.verbose = verbose
        
        # Initialize the self-query chain
        from langchain.chains.query_constructor.base import AttributeInfo
        from langchain.retrievers.self_query.base import SelfQueryRetriever as LCSelfQueryRetriever
        
        # Convert metadata field info to AttributeInfo objects
        attribute_info = []
        for field in self.metadata_field_info:
            attribute_info.append(
                AttributeInfo(
                    name=field["name"],
                    description=field.get("description", ""),
                    type=field.get("type", "string"),
                )
            )
        
        # Create the self-query retriever
        self.retriever = LCSelfQueryRetriever.from_llm(
            llm=self.llm,
            vectorstore=self.vectorstore,
            document_contents=self.document_contents,
            metadata_field_info=attribute_info,
            structured_query_translator=self.structured_query_translator,
            verbose=self.verbose,
        )
    
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
        return self.retriever.get_relevant_documents(query, callbacks=run_manager.get_child())
    
    @classmethod
    def from_llm(
        cls,
        vectorstore: Any,
        llm: BaseLanguageModel,
        document_contents: str,
        metadata_field_info: List[Dict[str, Any]],
        structured_query_translator: Optional[Any] = None,
        verbose: bool = False,
    ) -> "SelfQueryRetriever":
        """Create a self-query retriever.
        
        Args:
            vectorstore: Vector store to use
            llm: Language model to use for generating queries
            document_contents: Description of the document contents
            metadata_field_info: Information about metadata fields
            structured_query_translator: Optional translator for structured queries
            verbose: Whether to print verbose output
            
        Returns:
            SelfQueryRetriever instance
        """
        return cls(
            vectorstore=vectorstore,
            llm=llm,
            document_contents=document_contents,
            metadata_field_info=metadata_field_info,
            structured_query_translator=structured_query_translator,
            verbose=verbose,
        )