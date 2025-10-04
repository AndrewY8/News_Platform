"""
Settings configuration for Deep News Agent
"""
import os
from dotenv import load_dotenv

load_dotenv()


# Database settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Pipeline settings
DEFAULT_MAX_ITERATIONS = 5
DEFAULT_MAX_QUESTIONS_PER_ITERATION = 10
DEFAULT_ENABLE_EARNINGS_RETRIEVAL = True

# LLM settings
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
