import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

class Config:
    """Application configuration."""
    
    # YouTube API
    YOUTUBE_API_KEY = os.getenv('YT_API_KEY')
    
    # Database
    DB_PATH = os.getenv('DB_PATH', 'data/ranking.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Update settings
    UPDATE_INTERVAL_HOURS = 24
    
    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        if not cls.YOUTUBE_API_KEY:
            raise ValueError("YT_API_KEY not found in environment variables")
