"""Web-based document loaders for Langchain integration."""

from typing import List, Optional, Dict, Any, Union, Callable
from urllib.parse import urlparse

from langchain_community.document_loaders import WebBaseLoader, RecursiveUrlLoader
from langchain_core.documents import Document


class WebPageLoader:
    """Wrapper for Langchain's WebBaseLoader."""
    
    def __init__(
        self,
        web_path: str,
        header_template: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
        continue_on_failure: bool = False,
    ):
        """Initialize the WebPageLoader.
        
        Args:
            web_path: URL of the webpage to load
            header_template: Optional headers to use for the request
            verify_ssl: Whether to verify SSL certificates
            continue_on_failure: Whether to continue on failure
        """
        self.web_path = web_path
        self.header_template = header_template or {}
        self.verify_ssl = verify_ssl
        self.continue_on_failure = continue_on_failure
        
        self.loader = WebBaseLoader(
            web_path=web_path,
            header_template=self.header_template,
            verify_ssl=self.verify_ssl,
            continue_on_failure=self.continue_on_failure,
        )
        
    def load(self) -> List[Document]:
        """Load documents from the webpage.
        
        Returns:
            List of Document objects
        """
        return self.loader.load()
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if a URL is valid.
        
        Args:
            url: URL to check
            
        Returns:
            True if the URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False


class RecursiveWebPageLoader:
    """Wrapper for Langchain's RecursiveUrlLoader."""
    
    def __init__(
        self,
        url: str,
        max_depth: int = 2,
        extractor: Optional[Callable[[str], str]] = None,
        link_regex: str = r"href=[\"'](.*?)[\"']",
        exclude_dirs: Optional[List[str]] = None,
        timeout: int = 10,
        prevent_outside: bool = True,
    ):
        """Initialize the RecursiveWebPageLoader.
        
        Args:
            url: Base URL to start crawling from
            max_depth: Maximum depth to crawl
            extractor: Optional function to extract content from HTML
            link_regex: Regex to extract links from HTML
            exclude_dirs: Optional list of directories to exclude
            timeout: Timeout for requests in seconds
            prevent_outside: Whether to prevent crawling outside the base URL
        """
        self.url = url
        self.max_depth = max_depth
        self.extractor = extractor
        self.link_regex = link_regex
        self.exclude_dirs = exclude_dirs or []
        self.timeout = timeout
        self.prevent_outside = prevent_outside
        
        self.loader = RecursiveUrlLoader(
            url=url,
            max_depth=max_depth,
            extractor=extractor,
            link_regex=link_regex,
            exclude_dirs=exclude_dirs,
            timeout=timeout,
            prevent_outside=prevent_outside,
        )
        
    def load(self) -> List[Document]:
        """Load documents from the webpages.
        
        Returns:
            List of Document objects
        """
        return self.loader.load()