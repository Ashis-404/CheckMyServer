"""
Logger module for Smart Server Monitoring System
Centralized logging to console and file
"""

import logging
import logging.handlers
import os
from datetime import datetime


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "server_checker.log")


def setup_logger() -> logging.Logger:
    """Initialize logging configuration"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    logger = logging.getLogger("ServerChecker")
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler with rotation (5MB max size, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger() -> logging.Logger:
    """Get the logger instance"""
    return logging.getLogger("ServerChecker")
