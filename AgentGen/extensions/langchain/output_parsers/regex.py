"""Regex output parser integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable, Type
import re

from langchain_core.output_parsers import BaseOutputParser


class RegexParser(BaseOutputParser):
    """Wrapper for Langchain's regex output parser."""
    
    def __init__(
        self,
        regex: str,
        output_keys: List[str] = None,
        default_output_key: str = None,
    ):
        """Initialize the RegexParser.
        
        Args:
            regex: Regular expression pattern to use for parsing
            output_keys: Keys to use for the output dictionary
            default_output_key: Default key to use if no output keys are provided
        """
        super().__init__()
        self.regex = regex
        self.output_keys = output_keys
        self.default_output_key = default_output_key or "output"
        
        # Compile the regex pattern
        self.pattern = re.compile(regex)
    
    def parse(self, text: str) -> Dict[str, str]:
        """Parse the output text.
        
        Args:
            text: Text to parse
            
        Returns:
            Dictionary with parsed values
        """
        # Search for the pattern in the text
        match = self.pattern.search(text)
        
        if not match:
            raise ValueError(f"Could not parse output: {text}")
        
        # If output keys are provided, use them to extract named groups
        if self.output_keys:
            if match.groups():
                # If we have unnamed groups, map them to output keys
                return {
                    key: value
                    for key, value in zip(self.output_keys, match.groups())
                }
            elif match.groupdict():
                # If we have named groups, use them directly
                return match.groupdict()
        
        # If no output keys are provided, return the entire match
        return {self.default_output_key: match.group(0)}
    
    def parse_all(self, text: str) -> List[Dict[str, str]]:
        """Parse all matches in the output text.
        
        Args:
            text: Text to parse
            
        Returns:
            List of dictionaries with parsed values
        """
        # Find all matches in the text
        matches = self.pattern.finditer(text)
        
        results = []
        for match in matches:
            # If output keys are provided, use them to extract named groups
            if self.output_keys:
                if match.groups():
                    # If we have unnamed groups, map them to output keys
                    results.append({
                        key: value
                        for key, value in zip(self.output_keys, match.groups())
                    })
                elif match.groupdict():
                    # If we have named groups, use them directly
                    results.append(match.groupdict())
            else:
                # If no output keys are provided, return the entire match
                results.append({self.default_output_key: match.group(0)})
        
        return results
    
    def get_format_instructions(self) -> str:
        """Get format instructions for the output parser.
        
        Returns:
            Format instructions
        """
        if self.output_keys:
            return f"Your response should match the regex pattern: {self.regex}\nThe output will be parsed into the following keys: {', '.join(self.output_keys)}"
        else:
            return f"Your response should match the regex pattern: {self.regex}"