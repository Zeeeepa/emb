"""Multi-query retriever integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.language_models import BaseLanguageModel


class MultiQueryRetriever(BaseRetriever):
    """Wrapper for Langchain's multi-query retriever."""
    
    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLanguageModel,
        query_count: int = 3,
        use_prompt_template: bool = True,
        prompt_template: Optional[str] = None,
    ):
        """Initialize the MultiQueryRetriever.
        
        Args:
            retriever: Base retriever to use
            llm: Language model to use for generating queries
            query_count: Number of queries to generate
            use_prompt_template: Whether to use a prompt template
            prompt_template: Optional custom prompt template
        """
        super().__init__()
        self.retriever = retriever
        self.llm = llm
        self.query_count = query_count
        self.use_prompt_template = use_prompt_template
        self.prompt_template = prompt_template
        
        # Set default prompt template if not provided
        if self.use_prompt_template and not self.prompt_template:
            self.prompt_template = """You are an AI language model assistant. Your task is to generate {query_count} 
different versions of the given user question to retrieve relevant documents from a vector 
database. By generating multiple perspectives on the same question, we can ensure better 
document retrieval and provide the most helpful response to the user.

Original question: {question}

Generate {query_count} different versions of this question that will help us better 
retrieve relevant documents. Make sure the questions are diverse in perspective but 
still focused on the user's original intent.

Output these {query_count} questions as a numbered list:"""
    
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
        # Generate multiple queries
        queries = self._generate_queries(query)
        
        # Get documents for each query
        all_docs = []
        for q in queries:
            docs = self.retriever.get_relevant_documents(q, callbacks=run_manager.get_child())
            all_docs.extend(docs)
        
        # Remove duplicates
        unique_docs = self._get_unique_docs(all_docs)
        
        return unique_docs
    
    def _generate_queries(self, query: str) -> List[str]:
        """Generate multiple queries from the original query.
        
        Args:
            query: Original query string
            
        Returns:
            List of generated queries
        """
        if self.use_prompt_template:
            prompt = self.prompt_template.format(
                question=query,
                query_count=self.query_count
            )
            
            # Generate queries using the LLM
            response = self.llm.invoke(prompt)
            
            # Parse the response to extract queries
            queries = self._parse_queries(response.content, query)
        else:
            # Use a simpler approach if no prompt template
            from langchain.output_parsers import RegexParser
            
            output_parser = RegexParser(
                regex=r"(?P<query>.*?)(?:\n|$)",
                output_keys=["query"],
            )
            
            prompt = f"Generate {self.query_count} different versions of this query: {query}"
            response = self.llm.invoke(prompt)
            
            # Parse the response
            parsed_responses = output_parser.parse_all(response.content)
            queries = [pr["query"] for pr in parsed_responses]
            
            # Ensure we have the right number of queries
            if len(queries) < self.query_count:
                queries.extend([query] * (self.query_count - len(queries)))
            elif len(queries) > self.query_count:
                queries = queries[:self.query_count]
        
        # Always include the original query
        if query not in queries:
            queries.append(query)
            
        return queries
    
    def _parse_queries(self, response: str, original_query: str) -> List[str]:
        """Parse the LLM response to extract queries.
        
        Args:
            response: LLM response
            original_query: Original query string
            
        Returns:
            List of parsed queries
        """
        # Split the response by newlines and filter out empty lines
        lines = [line.strip() for line in response.split("\n") if line.strip()]
        
        # Extract queries (assuming they're in a numbered list format)
        queries = []
        for line in lines:
            # Try to extract queries from numbered lists (e.g., "1. query")
            if line[0].isdigit() and ". " in line:
                query = line.split(". ", 1)[1].strip()
                queries.append(query)
            # Also check for queries without numbers
            elif line and not line.startswith("#") and not line.startswith("-"):
                queries.append(line)
        
        # If we couldn't extract any queries, use the original query
        if not queries:
            queries = [original_query]
        
        # Ensure we have the right number of queries
        if len(queries) < self.query_count:
            queries.extend([original_query] * (self.query_count - len(queries)))
        elif len(queries) > self.query_count:
            queries = queries[:self.query_count]
        
        return queries
    
    def _get_unique_docs(self, docs: List[Document]) -> List[Document]:
        """Remove duplicate documents.
        
        Args:
            docs: List of documents
            
        Returns:
            List of unique documents
        """
        unique_docs = []
        seen_contents = set()
        
        for doc in docs:
            content = doc.page_content
            if content not in seen_contents:
                seen_contents.add(content)
                unique_docs.append(doc)
        
        return unique_docs
    
    @classmethod
    def from_llm(
        cls,
        retriever: BaseRetriever,
        llm: BaseLanguageModel,
        query_count: int = 3,
        use_prompt_template: bool = True,
        prompt_template: Optional[str] = None,
    ) -> "MultiQueryRetriever":
        """Create a multi-query retriever.
        
        Args:
            retriever: Base retriever to use
            llm: Language model to use for generating queries
            query_count: Number of queries to generate
            use_prompt_template: Whether to use a prompt template
            prompt_template: Optional custom prompt template
            
        Returns:
            MultiQueryRetriever instance
        """
        return cls(
            retriever=retriever,
            llm=llm,
            query_count=query_count,
            use_prompt_template=use_prompt_template,
            prompt_template=prompt_template,
        )