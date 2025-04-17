"""
Configuration settings for the application.
"""

import os
from typing import Dict, Any

class Config:
    """Configuration settings."""
    
    # LLM settings
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    
    # LLM model settings
    DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
    MAX_TOKENS = 1000
    
    # File paths
    DEFAULT_OUTPUT_DIR = "output"
    
    # Database settings (placeholder for future implementation)
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "5432"))
    DB_NAME = os.environ.get("DB_NAME", "tms")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
    
    # API settings
    API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.com")
    API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "30"))
    
    # Logging settings
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", "")
    
    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "database": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }