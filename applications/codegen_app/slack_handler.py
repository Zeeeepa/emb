"""
Slack event handler for the Codegen App.

This module provides functions for handling Slack events and sending messages to Slack.
"""

import logging
import os
from typing import Dict, Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_NOTIFICATION_CHANNEL = os.getenv("SLACK_NOTIFICATION_CHANNEL", "")

class SlackHandler:
    """Handler for Slack events and messages."""
    
    def __init__(self, token: str = SLACK_BOT_TOKEN):
        """Initialize the Slack handler with the bot token."""
        self.client = WebClient(token=token)
        self.default_channel = SLACK_NOTIFICATION_CHANNEL
    
    def send_message(self, text: str, channel: str = None, thread_ts: str = None) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            text: The message text
            channel: The channel ID (defaults to SLACK_NOTIFICATION_CHANNEL)
            thread_ts: Thread timestamp to reply in a thread
            
        Returns:
            The Slack API response
        """
        try:
            channel_id = channel or self.default_channel
            if not channel_id:
                logger.error("No channel specified and no default channel set")
                return {"ok": False, "error": "No channel specified"}
            
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts
            )
            return response
        except SlackApiError as e:
            logger.error(f"Error sending message to Slack: {e}")
            return {"ok": False, "error": str(e)}
    
    def send_blocks(self, blocks: list, channel: str = None, thread_ts: str = None) -> Dict[str, Any]:
        """
        Send a message with blocks to a Slack channel.
        
        Args:
            blocks: The message blocks
            channel: The channel ID (defaults to SLACK_NOTIFICATION_CHANNEL)
            thread_ts: Thread timestamp to reply in a thread
            
        Returns:
            The Slack API response
        """
        try:
            channel_id = channel or self.default_channel
            if not channel_id:
                logger.error("No channel specified and no default channel set")
                return {"ok": False, "error": "No channel specified"}
            
            response = self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                thread_ts=thread_ts
            )
            return response
        except SlackApiError as e:
            logger.error(f"Error sending blocks to Slack: {e}")
            return {"ok": False, "error": str(e)}
    
    def handle_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle a Slack event.
        
        Args:
            event: The Slack event payload
            
        Returns:
            A response to send back to Slack, or None
        """
        # Handle URL verification challenge
        if event.get("type") == "url_verification":
            return {"challenge": event.get("challenge")}
        
        # Handle event callbacks
        if event.get("type") == "event_callback":
            inner_event = event.get("event", {})
            event_type = inner_event.get("type")
            
            # Handle message events
            if event_type == "message":
                return self._handle_message(inner_event)
            
            # Handle app_mention events
            elif event_type == "app_mention":
                return self._handle_app_mention(inner_event)
        
        # Default response for unhandled events
        return {"ok": True, "message": "Event received"}
    
    def _handle_message(self, message_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a message event.
        
        Args:
            message_event: The message event payload
            
        Returns:
            A response to send back to Slack
        """
        # Skip messages from bots to avoid loops
        if message_event.get("bot_id"):
            return {"ok": True, "message": "Skipping bot message"}
        
        # Get message details
        user = message_event.get("user")
        text = message_event.get("text", "")
        channel = message_event.get("channel")
        ts = message_event.get("ts")
        
        logger.info(f"Received message from {user} in {channel}: {text}")
        
        # Process the message (you can add your own logic here)
        # For now, we'll just acknowledge it
        return {"ok": True, "message": "Message processed"}
    
    def _handle_app_mention(self, mention_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an app_mention event.
        
        Args:
            mention_event: The app_mention event payload
            
        Returns:
            A response to send back to Slack
        """
        # Get mention details
        user = mention_event.get("user")
        text = mention_event.get("text", "")
        channel = mention_event.get("channel")
        ts = mention_event.get("ts")
        
        logger.info(f"Bot was mentioned by {user} in {channel}: {text}")
        
        # Send a response
        self.send_message(
            text=f"Hi <@{user}>! I received your message. I'm the Codegen Assistant and I can help you with code analysis, PR suggestions, and more.",
            channel=channel,
            thread_ts=ts
        )
        
        return {"ok": True, "message": "App mention processed"}

# Create a singleton instance
slack_handler = SlackHandler()