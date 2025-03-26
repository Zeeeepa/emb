"""JSON output parser integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable, Type
import json
import re

from langchain_core.output_parsers import BaseOutputParser


class JsonOutputParser(BaseOutputParser):
    """Wrapper for Langchain's JSON output parser."""
    
    def __init__(
        self,
        pydantic_object: Optional[Type] = None,
    ):
        """Initialize the JsonOutputParser.
        
        Args:
            pydantic_object: Optional Pydantic model to use for parsing
        """
        super().__init__()
        self.pydantic_object = pydantic_object
    
    def parse(self, text: str) -> Any:
        """Parse the output text.
        
        Args:
            text: Text to parse
            
        Returns:
            Parsed output
        """
        try:
            # Try to parse as JSON
            json_object = json.loads(text)
            
            # If a Pydantic model is provided, validate the JSON
            if self.pydantic_object is not None:
                return self.pydantic_object.parse_obj(json_object)
            
            return json_object
        except json.JSONDecodeError:
            # If not valid JSON, try to extract JSON from the text
            return self._extract_json_from_text(text)
    
    def _extract_json_from_text(self, text: str) -> Any:
        """Extract JSON from text.
        
        Args:
            text: Text to extract JSON from
            
        Returns:
            Parsed output
        """
        # Look for JSON-like patterns in the text
        # First, try to find content between triple backticks
        json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(json_pattern, text)
        
        if match:
            json_str = match.group(1)
            try:
                json_object = json.loads(json_str)
                
                # If a Pydantic model is provided, validate the JSON
                if self.pydantic_object is not None:
                    return self.pydantic_object.parse_obj(json_object)
                
                return json_object
            except json.JSONDecodeError:
                pass
        
        # If no match with backticks, try to find JSON object directly
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = text[start_idx:end_idx + 1]
            try:
                json_object = json.loads(json_str)
                
                # If a Pydantic model is provided, validate the JSON
                if self.pydantic_object is not None:
                    return self.pydantic_object.parse_obj(json_object)
                
                return json_object
            except json.JSONDecodeError:
                pass
        
        # If we can't extract valid JSON, raise an error
        raise ValueError(f"Could not parse output as JSON: {text}")
    
    def get_format_instructions(self) -> str:
        """Get format instructions for the output parser.
        
        Returns:
            Format instructions
        """
        if self.pydantic_object is not None:
            schema = self.pydantic_object.schema()
            
            # Extract relevant parts of the schema
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Build format instructions
            instructions = "Return a JSON object with the following structure:\n\n```json\n{\n"
            
            for name, prop in properties.items():
                description = prop.get("description", "")
                type_str = prop.get("type", "string")
                
                # Format the property
                if name in required:
                    instructions += f'  "{name}": {type_str} // Required. {description}\n'
                else:
                    instructions += f'  "{name}": {type_str} // Optional. {description}\n'
            
            instructions += "}\n```"
            
            return instructions
        else:
            return "Return a JSON object."