"""List output parser integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable, Type
import re

from langchain_core.output_parsers import BaseOutputParser


class CommaSeparatedListOutputParser(BaseOutputParser):
    """Wrapper for Langchain's comma-separated list output parser."""
    
    def __init__(
        self,
        strip_whitespace: bool = True,
        lowercase: bool = False,
    ):
        """Initialize the CommaSeparatedListOutputParser.
        
        Args:
            strip_whitespace: Whether to strip whitespace from items
            lowercase: Whether to convert items to lowercase
        """
        super().__init__()
        self.strip_whitespace = strip_whitespace
        self.lowercase = lowercase
    
    def parse(self, text: str) -> List[str]:
        """Parse the output text.
        
        Args:
            text: Text to parse
            
        Returns:
            List of items
        """
        # Split by commas
        items = text.split(",")
        
        # Process items
        if self.strip_whitespace:
            items = [item.strip() for item in items]
        
        if self.lowercase:
            items = [item.lower() for item in items]
        
        # Filter out empty items
        items = [item for item in items if item]
        
        return items
    
    def get_format_instructions(self) -> str:
        """Get format instructions for the output parser.
        
        Returns:
            Format instructions
        """
        return "Your response should be a comma-separated list of items, e.g., item1, item2, item3"


class NumberedListOutputParser(BaseOutputParser):
    """Parser for numbered list outputs."""
    
    def __init__(
        self,
        strip_whitespace: bool = True,
        lowercase: bool = False,
    ):
        """Initialize the NumberedListOutputParser.
        
        Args:
            strip_whitespace: Whether to strip whitespace from items
            lowercase: Whether to convert items to lowercase
        """
        super().__init__()
        self.strip_whitespace = strip_whitespace
        self.lowercase = lowercase
    
    def parse(self, text: str) -> List[str]:
        """Parse the output text.
        
        Args:
            text: Text to parse
            
        Returns:
            List of items
        """
        # Look for numbered list items (e.g., "1. Item", "1) Item")
        pattern = r"(?:\d+[\.\)]\s*)(.*?)(?=\n\d+[\.\)]|\n\n|$)"
        matches = re.findall(pattern, "\n" + text)
        
        if not matches:
            # If no numbered list found, try to split by newlines
            items = text.split("\n")
            # Remove any numbering at the beginning of lines
            items = [re.sub(r"^\d+[\.\)]\s*", "", item) for item in items]
        else:
            items = matches
        
        # Process items
        if self.strip_whitespace:
            items = [item.strip() for item in items]
        
        if self.lowercase:
            items = [item.lower() for item in items]
        
        # Filter out empty items
        items = [item for item in items if item]
        
        return items
    
    def get_format_instructions(self) -> str:
        """Get format instructions for the output parser.
        
        Returns:
            Format instructions
        """
        return "Your response should be a numbered list of items, e.g.:\n1. Item 1\n2. Item 2\n3. Item 3"