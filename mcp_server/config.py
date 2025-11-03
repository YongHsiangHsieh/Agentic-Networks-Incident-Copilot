"""
MCP Server configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Server configuration
SERVER_NAME = "network-copilot"
SERVER_VERSION = "1.0.0"

# AWS Configuration (reuse from ai_config)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Debug mode
DEBUG = os.getenv("DEBUG_AI", "false").lower() == "true"

