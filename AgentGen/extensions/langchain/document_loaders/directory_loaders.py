"""Directory-based document loaders for Langchain integration."""

from typing import List, Optional, Dict, Any, Union, Callable
from pathlib import Path
import os

from langchain_community.document_loaders import DirectoryLoader as LCDirectoryLoader
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document


class DirectoryLoader:
    """Wrapper for Langchain's DirectoryLoader."""
    
    def __init__(
        self,
        path: str,
        glob: str = "**/*.txt",
        loader_cls: Any = TextLoader,
        loader_kwargs: Optional[Dict[str, Any]] = None,
        recursive: bool = False,
        show_progress: bool = False,
        use_multithreading: bool = False,
        max_concurrency: Optional[int] = None,
    ):
        """Initialize the DirectoryLoader.
        
        Args:
            path: Path to the directory
            glob: Glob pattern to match files
            loader_cls: Document loader class to use for each file
            loader_kwargs: Optional arguments to pass to the loader
            recursive: Whether to search recursively
            show_progress: Whether to show a progress bar
            use_multithreading: Whether to use multithreading
            max_concurrency: Maximum number of threads to use
        """
        self.path = path
        self.glob = glob
        self.loader_cls = loader_cls
        self.loader_kwargs = loader_kwargs or {}
        self.recursive = recursive
        self.show_progress = show_progress
        self.use_multithreading = use_multithreading
        self.max_concurrency = max_concurrency
        
        self.loader = LCDirectoryLoader(
            path=path,
            glob=glob,
            loader_cls=loader_cls,
            loader_kwargs=self.loader_kwargs,
            recursive=recursive,
            show_progress=show_progress,
            use_multithreading=use_multithreading,
            max_concurrency=max_concurrency,
        )
        
    def load(self) -> List[Document]:
        """Load documents from the directory.
        
        Returns:
            List of Document objects
        """
        return self.loader.load()


class RecursiveDirectoryLoader(DirectoryLoader):
    """Wrapper for Langchain's DirectoryLoader with recursive loading."""
    
    def __init__(
        self,
        path: str,
        glob: str = "**/*.txt",
        loader_cls: Any = TextLoader,
        loader_kwargs: Optional[Dict[str, Any]] = None,
        show_progress: bool = False,
        use_multithreading: bool = False,
        max_concurrency: Optional[int] = None,
        exclude_patterns: Optional[List[str]] = None,
    ):
        """Initialize the RecursiveDirectoryLoader.
        
        Args:
            path: Path to the directory
            glob: Glob pattern to match files
            loader_cls: Document loader class to use for each file
            loader_kwargs: Optional arguments to pass to the loader
            show_progress: Whether to show a progress bar
            use_multithreading: Whether to use multithreading
            max_concurrency: Maximum number of threads to use
            exclude_patterns: Optional list of patterns to exclude
        """
        self.exclude_patterns = exclude_patterns or []
        
        super().__init__(
            path=path,
            glob=glob,
            loader_cls=loader_cls,
            loader_kwargs=loader_kwargs,
            recursive=True,  # Always recursive
            show_progress=show_progress,
            use_multithreading=use_multithreading,
            max_concurrency=max_concurrency,
        )
    
    def load(self) -> List[Document]:
        """Load documents from the directory recursively, excluding specified patterns.
        
        Returns:
            List of Document objects
        """
        documents = self.loader.load()
        
        # Filter out documents that match exclude patterns
        if self.exclude_patterns:
            filtered_docs = []
            for doc in documents:
                source = doc.metadata.get("source", "")
                if not any(pattern in source for pattern in self.exclude_patterns):
                    filtered_docs.append(doc)
            return filtered_docs
        
        return documents