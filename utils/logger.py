import os
import sys
from datetime import datetime
from loguru import logger

# Configure logger
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Default log format
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Configure loguru
logger.configure(
    handlers=[
        # Console handler
        {
            "sink": sys.stdout, 
            "format": log_format,
            "level": "INFO",
            "colorize": True,
        },
        # File handler
        {
            "sink": os.path.join(LOG_DIR, f"mlb_podcast_{datetime.now().strftime('%Y-%m-%d')}.log"),
            "format": log_format,
            "level": "DEBUG",
            "rotation": "1 day",
            "retention": "1 week",
        },
    ]
)

def get_logger(name):
    """Get a named logger instance."""
    return logger.bind(name=name)