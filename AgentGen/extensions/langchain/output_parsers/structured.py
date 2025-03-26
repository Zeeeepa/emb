"""Structured output parser integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable, Type
import json
from pydantic import BaseModel, create_model, Field

from langchain_core.output_parsers import BaseOutputParser


class StructuredOutputParser(BaseOutputParser):
    """Wrapper for Langchain's structured output parser."""
    
    def __init__(
        self,
        pydantic_object: Type[BaseModel] = None,
        schema: Dict[str, Any] = None,
    ):
        """Initialize the StructuredOutputParser.
        
        Args:
            pydantic_object: Pydantic model to use for parsing
            schema: Schema to use for parsing (alternative to pydantic_object)
        """
        super().__init__()
        
        if pydantic_object is not None:
            self.pydantic_object = pydantic_object
        elif schema is not None:
            # Create a Pydantic model from the schema
            fields = {}
            for name, field_info in schema.items():
                field_type = field_info.get("type", str)
                field_description = field_info.get("description", "")
                
                # Convert string type names to actual types
                if isinstance(field_type, str):
                    if field_type.lower() == "string":
                        field_type = str
                    elif field_type.lower() == "integer":
                        field_type = int
                    elif field_type.lower() == "number":
                        field_type = float
                    elif field_type.lower() == "boolean":
                        field_type = bool
                    elif field_type.lower() == "array":
                        field_type = List[str]  # Default to list of strings
                    elif field_type.lower() == "object":
                        field_type = Dict[str, Any]  # Default to dictionary
                
                fields[name] = (field_type, Field(description=field_description))
            
            self.pydantic_object = create_model("DynamicModel", **fields)
        else:
            raise ValueError("Either pydantic_object or schema must be provided")
    
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
            return self.pydantic_object.parse_obj(json_object)
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
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = text[start_idx:end_idx + 1]
            try:
                json_object = json.loads(json_str)
                return self.pydantic_object.parse_obj(json_object)
            except (json.JSONDecodeError, ValueError):
                pass
        
        # If we can't extract valid JSON, raise an error
        raise ValueError(f"Could not parse output: {text}")
    
    def get_format_instructions(self) -> str:
        """Get format instructions for the output parser.
        
        Returns:
            Format instructions
        """
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
    
    @classmethod
    def from_pydantic_model(cls, pydantic_object: Type[BaseModel]) -> "StructuredOutputParser":
        """Create a parser from a Pydantic model.
        
        Args:
            pydantic_object: Pydantic model to use for parsing
            
        Returns:
            StructuredOutputParser instance
        """
        return cls(pydantic_object=pydantic_object)
    
    @classmethod
    def from_schema(cls, schema: Dict[str, Any]) -> "StructuredOutputParser":
        """Create a parser from a schema.
        
        Args:
            schema: Schema to use for parsing
            
        Returns:
            StructuredOutputParser instance
        """
        return cls(schema=schema)