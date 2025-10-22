"""
Configuration module for the log aggregator service.
Handles environment variables and application settings.
"""
import os
from pathlib import Path

class Config:
    """Application configuration"""
    
    # Application settings
    APP_NAME = "UTS Log Aggregator"
    APP_VERSION = "1.0.0"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8080"))
    
    # Database settings
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
    DB_PATH = DATA_DIR / "dedup_store.db"
    
    # Queue settings
    QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", "10000"))
    
    # Consumer settings
    CONSUMER_BATCH_SIZE = int(os.getenv("CONSUMER_BATCH_SIZE", "100"))
    CONSUMER_SLEEP_INTERVAL = float(os.getenv("CONSUMER_SLEEP_INTERVAL", "0.01"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def ensure_data_dir(cls):
        """Ensure data directory exists"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
