"""Document loaders integration for Langchain."""

from agentgen.extensions.langchain.document_loaders.file_loaders import (
    TextFileLoader,
    PDFFileLoader,
    CSVFileLoader,
    JSONFileLoader,
    HTMLFileLoader,
)
from agentgen.extensions.langchain.document_loaders.web_loaders import (
    WebPageLoader,
    RecursiveWebPageLoader,
)
from agentgen.extensions.langchain.document_loaders.directory_loaders import (
    DirectoryLoader,
    RecursiveDirectoryLoader,
)

__all__ = [
    "TextFileLoader",
    "PDFFileLoader",
    "CSVFileLoader",
    "JSONFileLoader",
    "HTMLFileLoader",
    "WebPageLoader",
    "RecursiveWebPageLoader",
    "DirectoryLoader",
    "RecursiveDirectoryLoader",
]