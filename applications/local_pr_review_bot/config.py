import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Config:
    # GitHub configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    TRIGGER_LABEL: str = os.getenv("TRIGGER_LABEL", "analyzer")
    WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET")
    
    # Server configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # LLM configuration
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Slack configuration (optional)
    SLACK_BOT_TOKEN: Optional[str] = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET: Optional[str] = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_NOTIFICATION_CHANNEL: Optional[str] = os.getenv("SLACK_NOTIFICATION_CHANNEL")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Validate configuration
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        if not cls.GITHUB_TOKEN:
            print("ERROR: GITHUB_TOKEN is required")
            return False
            
        if not (cls.ANTHROPIC_API_KEY or cls.OPENAI_API_KEY):
            print("ERROR: Either ANTHROPIC_API_KEY or OPENAI_API_KEY is required")
            return False
            
        return True