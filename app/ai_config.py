"""
AI/LLM configuration for AWS Bedrock integration.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AIConfig:
    """Configuration for AWS Bedrock AI models."""
    
    # AWS Bedrock settings
    BEDROCK_REGION = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_MODEL = os.getenv(
        "BEDROCK_MODEL", 
        "anthropic.claude-3-haiku-20240307-v1:0"
    )
    
    # Available models:
    # - anthropic.claude-3-haiku-20240307-v1:0 (fastest, cheapest)
    # - anthropic.claude-3-sonnet-20240229-v1:0 (balanced)
    # - anthropic.claude-3-5-sonnet-20240620-v1:0 (most capable)
    
    # Model parameters
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    
    # Feature flags
    USE_AI_HYPOTHESIS = os.getenv("USE_AI_HYPOTHESIS", "true").lower() == "true"
    USE_AI_RANKING = os.getenv("USE_AI_RANKING", "true").lower() == "true"
    FALLBACK_ON_ERROR = os.getenv("FALLBACK_ON_ERROR", "true").lower() == "true"
    
    # Debug mode
    DEBUG_AI = os.getenv("DEBUG_AI", "false").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if not os.getenv("AWS_ACCESS_KEY_ID"):
            print("WARNING: AWS_ACCESS_KEY_ID not set. AWS Bedrock calls may fail.")
        if not os.getenv("AWS_SECRET_ACCESS_KEY"):
            print("WARNING: AWS_SECRET_ACCESS_KEY not set. AWS Bedrock calls may fail.")
        
        if cls.DEBUG_AI:
            print(f"AI Config:")
            print(f"  Region: {cls.BEDROCK_REGION}")
            print(f"  Model: {cls.BEDROCK_MODEL}")
            print(f"  Temperature: {cls.LLM_TEMPERATURE}")
            print(f"  Max Tokens: {cls.LLM_MAX_TOKENS}")
            print(f"  AI Hypothesis: {cls.USE_AI_HYPOTHESIS}")

