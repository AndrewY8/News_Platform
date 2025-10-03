"""
API Keys configuration for Deep Research Agent
"""
import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


def get_api_keys() -> Dict[str, str]:
    """Get all required API keys from environment variables"""
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "tavily_api_key": os.getenv("TAVILY_API_KEY"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    }
