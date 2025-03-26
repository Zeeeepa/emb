"""File-based document loaders for Langchain integration."""

from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    JSONLoader,
    BSHTMLLoader,
)
from langchain_core.documents import Document


class TextFileLoader:
    """Wrapper for Langchain's TextLoader."""
    
    def __init__(self, file_path: str, encoding: str = "utf-8"):
        """Initialize the TextFileLoader.
        
        Args:
            file_path: Path to the text file
            encoding: File encoding (default: utf-8)
        """
        self.file_path = file_path
        self.encoding = encoding
        self.loader = TextLoader(file_path, encoding=encoding)
        
    def load(self) -> List[Document]:
        """Load documents from the text file.
        
        Returns:
            List of Document objects
        """
        return self.loader.load()


class PDFFileLoader:
    """Wrapper for Langchain's PyPDFLoader."""
    
    def __init__(self, file_path: str):
        """Initialize the PDFFileLoader.
        
        Args:
            file_path: Path to the PDF file
        """
        self.file_path = file_path
        self.loader = PyPDFLoader(file_path)
        
    def load(self) -> List[Document]:
        """Load documents from the PDF file.
        
        Returns:
            List of Document objects, one per page
        """
        return self.loader.load()
    
    def load_and_split(self, text_splitter=None) -> List[Document]:
        """Load and split the PDF into chunks.
        
        Args:
            text_splitter: Optional text splitter to use
            
        Returns:
            List of Document objects after splitting
        """
        if text_splitter:
            return self.loader.load_and_split(text_splitter)
        return self.loader.load_and_split()


class CSVFileLoader:
    """Wrapper for Langchain's CSVLoader."""
    
    def __init__(
        self, 
        file_path: str,
        csv_args: Optional[Dict[str, Any]] = None,
        source_column: Optional[str] = None,
    ):
        """Initialize the CSVFileLoader.
        
        Args:
            file_path: Path to the CSV file
            csv_args: Optional arguments to pass to the CSV reader
            source_column: Optional column to use as the source
        """
        self.file_path = file_path
        self.csv_args = csv_args or {}
        self.source_column = source_column
        self.loader = CSVLoader(
            file_path=file_path,
            csv_args=self.csv_args,
            source_column=self.source_column,
        )
        
    def load(self) -> List[Document]:
        """Load documents from the CSV file.
        
        Returns:
            List of Document objects, one per row
        """
        return self.loader.load()


class JSONFileLoader:
    """Wrapper for Langchain's JSONLoader."""
    
    def __init__(
        self,
        file_path: str,
        jq_schema: str = ".",
        content_key: Optional[str] = None,
        metadata_func: Optional[callable] = None,
    ):
        """Initialize the JSONLoader.
        
        Args:
            file_path: Path to the JSON file
            jq_schema: jq schema string to identify the elements to extract
            content_key: Key to use for content (if None, uses the entire selected object)
            metadata_func: Optional function to extract metadata from the selected object
        """
        self.file_path = file_path
        self.jq_schema = jq_schema
        self.content_key = content_key
        self.metadata_func = metadata_func
        self.loader = JSONLoader(
            file_path=file_path,
            jq_schema=jq_schema,
            content_key=content_key,
            metadata_func=metadata_func,
        )
        
    def load(self) -> List[Document]:
        """Load documents from the JSON file.
        
        Returns:
            List of Document objects
        """
        return self.loader.load()


class HTMLFileLoader:
    """Wrapper for Langchain's BSHTMLLoader."""
    
    def __init__(self, file_path: str, open_encoding: str = "utf-8"):
        """Initialize the HTMLFileLoader.
        
        Args:
            file_path: Path to the HTML file
            open_encoding: File encoding (default: utf-8)
        """
        self.file_path = file_path
        self.open_encoding = open_encoding
        self.loader = BSHTMLLoader(file_path, open_encoding=open_encoding)
        
    def load(self) -> List[Document]:
        """Load documents from the HTML file.
        
        Returns:
            List of Document objects
        """
        return self.loader.load()