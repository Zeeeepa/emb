"""Conversation entity memory integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable, Set
import os
import json

from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, get_buffer_string
from langchain_core.language_models import BaseLanguageModel


class ConversationEntityMemory(BaseMemory):
    """Wrapper for Langchain's conversation entity memory."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory_key: str = "entities",
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
        entity_extraction_prompt: Optional[str] = None,
        entity_summarization_prompt: Optional[str] = None,
        k: int = 3,
    ):
        """Initialize the ConversationEntityMemory.
        
        Args:
            llm: Language model to use for entity extraction and summarization
            memory_key: Key to use for the memory in the chain
            input_key: Key to use for the input in the chain
            output_key: Key to use for the output in the chain
            human_prefix: Prefix for human messages
            ai_prefix: Prefix for AI messages
            entity_extraction_prompt: Optional custom prompt for entity extraction
            entity_summarization_prompt: Optional custom prompt for entity summarization
            k: Number of recent interactions to consider for entity extraction
        """
        super().__init__()
        self.llm = llm
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.human_prefix = human_prefix
        self.ai_prefix = ai_prefix
        self.entity_extraction_prompt = entity_extraction_prompt
        self.entity_summarization_prompt = entity_summarization_prompt
        self.k = k
        
        self.chat_memory = []
        self.entity_store = {}
        
        # Set default prompts if not provided
        if not self.entity_extraction_prompt:
            self.entity_extraction_prompt = """You are an AI assistant reading the transcript of a conversation between an AI and a human. Extract all entities from the conversation and return them as a JSON list of strings. Only extract entities that are proper nouns or technical terms.

Example:
Human: My name is John Doe and I work at Google. I'm interested in natural language processing and machine learning.
AI: That's great, John! Natural language processing and machine learning are fascinating fields. Google is doing some amazing work in these areas.

Output: ["John Doe", "Google", "natural language processing", "machine learning"]

Conversation:
{conversation}

Output:"""
            
        if not self.entity_summarization_prompt:
            self.entity_summarization_prompt = """You are an AI assistant reading the transcript of a conversation between an AI and a human. 
Given the entity {entity} and the conversation, create a concise summary about this entity based on the conversation.
If there isn't enough information about the entity, respond with "No information provided."

Example:
Entity: Machine Learning
Conversation:
Human: I'm interested in machine learning and its applications.
AI: Machine learning is a fascinating field with applications in computer vision, natural language processing, and more.
Human: I'm particularly interested in supervised learning algorithms.
AI: Supervised learning is a type of machine learning where the model is trained on labeled data.

Output: Machine learning is a field with applications in computer vision and NLP. It includes supervised learning, which involves training models on labeled data.

Entity: {entity}
Conversation:
{conversation}

Output:"""
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables.
        
        Args:
            inputs: Input values
            
        Returns:
            Dictionary with memory variables
        """
        # Return the entity store
        return {self.memory_key: self.entity_store}
    
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
        
        # Extract entities from the recent conversation
        self._extract_entities()
    
    def _extract_entities(self) -> None:
        """Extract entities from the conversation."""
        # Get the recent conversation
        recent_messages = self.chat_memory[-2 * self.k:] if len(self.chat_memory) > 2 * self.k else self.chat_memory
        
        # Get the buffer string of the conversation
        buffer = get_buffer_string(
            recent_messages,
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
        )
        
        # Prepare the prompt for entity extraction
        prompt = self.entity_extraction_prompt.format(conversation=buffer)
        
        # Extract entities
        response = self.llm.invoke(prompt).content
        
        # Parse the response to get entities
        try:
            # Try to parse as JSON
            entities = json.loads(response)
            if not isinstance(entities, list):
                entities = []
        except:
            # If parsing fails, try to extract entities from the text
            entities = self._extract_entities_from_text(response)
        
        # Update entity summaries
        for entity in entities:
            if entity not in self.entity_store:
                self._summarize_entity(entity, buffer)
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract entities from text when JSON parsing fails.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted entities
        """
        # Remove common formatting
        text = text.strip().strip('[]').strip('""')
        
        # Split by common delimiters
        if '", "' in text:
            return [item.strip().strip('"') for item in text.split('", "')]
        elif "', '" in text:
            return [item.strip().strip("'") for item in text.split("', '")]
        elif ',' in text:
            return [item.strip().strip('"').strip("'") for item in text.split(',')]
        else:
            return [text.strip().strip('"').strip("'")] if text else []
    
    def _summarize_entity(self, entity: str, conversation: str) -> None:
        """Summarize an entity based on the conversation.
        
        Args:
            entity: Entity to summarize
            conversation: Conversation context
        """
        # Prepare the prompt for entity summarization
        prompt = self.entity_summarization_prompt.format(
            entity=entity,
            conversation=conversation,
        )
        
        # Generate the summary
        summary = self.llm.invoke(prompt).content
        
        # Store the summary
        self.entity_store[entity] = summary
    
    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory = []
        self.entity_store = {}