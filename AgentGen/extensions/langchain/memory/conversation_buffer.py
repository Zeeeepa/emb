"""Conversation buffer memory integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os

from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, get_buffer_string


class ConversationBufferMemory(BaseMemory):
    """Wrapper for Langchain's conversation buffer memory."""
    
    def __init__(
        self,
        memory_key: str = "history",
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        return_messages: bool = False,
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
    ):
        """Initialize the ConversationBufferMemory.
        
        Args:
            memory_key: Key to use for the memory in the chain
            input_key: Key to use for the input in the chain
            output_key: Key to use for the output in the chain
            return_messages: Whether to return the messages directly
            human_prefix: Prefix for human messages
            ai_prefix: Prefix for AI messages
        """
        super().__init__()
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.return_messages = return_messages
        self.human_prefix = human_prefix
        self.ai_prefix = ai_prefix
        self.chat_memory = []
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables.
        
        Args:
            inputs: Input values
            
        Returns:
            Dictionary with memory variables
        """
        if self.return_messages:
            return {self.memory_key: self.chat_memory}
        else:
            return {self.memory_key: get_buffer_string(
                self.chat_memory,
                human_prefix=self.human_prefix,
                ai_prefix=self.ai_prefix,
            )}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save context from this conversation turn.
        
        Args:
            inputs: Input values
            outputs: Output values
        """
        # Get input and output keys
        input_key = self.input_key if self.input_key is not None else list(inputs.keys())[0]
        output_key = self.output_key if self.output_key is not None else list(outputs.keys())[0]
        
        # Save the context
        from langchain_core.messages import HumanMessage, AIMessage
        
        self.chat_memory.append(HumanMessage(content=inputs[input_key]))
        self.chat_memory.append(AIMessage(content=outputs[output_key]))
    
    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory = []