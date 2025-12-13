"""
Logging configuration and utilities.

Centralizes logging setup for the application.
"""

import logging
from pathlib import Path
from typing import Optional

from natural_gas_g5.config.settings import config


def setup_logging(
    log_file: Optional[str] = None,
    level: Optional[str] = None,
    encoding: Optional[str] = None
) -> None:
    """
    Configure application logging.
    
    Args:
        log_file: Path to log file (default: from config)
        level: Logging level (default: from config)
        encoding: File encoding (default: from config)
        
    Examples:
        >>> setup_logging()  # Uses defaults from config
        >>> setup_logging(level="DEBUG")  # Override level
    """
    # Use config defaults if not specified
    log_file = log_file or config.LOG_FILE
    level = level or config.LOG_LEVEL
    encoding = encoding or config.LOG_ENCODING
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure logging
    logging.basicConfig(
        filename=log_file,
        filemode='a',  # Append mode
        level=numeric_level,
        encoding=encoding,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Log initialization
    logging.info("=" * 60)
    logging.info("Doğal Gaz Özellikleri G5 başlatıldı")
    logging.info(f"Log seviyesi: {level}")
    logging.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Configured logger instance
        
    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Calculation started")
    """
    return logging.getLogger(name)
