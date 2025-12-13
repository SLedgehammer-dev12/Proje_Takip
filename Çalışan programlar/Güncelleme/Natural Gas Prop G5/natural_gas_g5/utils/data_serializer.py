"""
Data serialization utilities for saving and loading user inputs.

Provides JSON-based save/load functionality for gas composition and calculation parameters.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# File extension for saved data
FILE_EXTENSION = ".ngp"
FILE_TYPE_NAME = "Natural Gas Properties"

# Current schema version
SCHEMA_VERSION = "1.0"


class DataSerializationError(Exception):
    """Error during data serialization or deserialization."""
    pass


def save_inputs_to_file(data: Dict[str, Any], filepath: str) -> None:
    """
    Save user inputs to a JSON file.
    
    Args:
        data: Dictionary containing user inputs
        filepath: Path to save the file
        
    Raises:
        DataSerializationError: If save fails
    """
    try:
        # Add schema version
        save_data = {
            "version": SCHEMA_VERSION,
            **data
        }
        
        # Ensure .ngp extension
        if not filepath.endswith(FILE_EXTENSION):
            filepath += FILE_EXTENSION
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        raise DataSerializationError(f"Kaydetme hatası: {e}")


def load_inputs_from_file(filepath: str) -> Dict[str, Any]:
    """
    Load user inputs from a JSON file.
    
    Args:
        filepath: Path to the file to load
        
    Returns:
        Dictionary containing user inputs
        
    Raises:
        DataSerializationError: If load fails or file is invalid
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate schema version
        version = data.get("version", "0.0")
        if not version.startswith("1."):
            logger.warning(f"Unknown file version: {version}")
        
        logger.info(f"Data loaded from {filepath}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        raise DataSerializationError(f"Geçersiz dosya formatı: {e}")
    except FileNotFoundError:
        raise DataSerializationError("Dosya bulunamadı")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise DataSerializationError(f"Yükleme hatası: {e}")


def validate_loaded_data(data: Dict[str, Any]) -> bool:
    """
    Validate that loaded data has required fields.
    
    Args:
        data: Loaded data dictionary
        
    Returns:
        True if data is valid, False otherwise
    """
    required_fields = ["composition"]
    
    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False
    
    # Validate composition structure
    composition = data.get("composition", [])
    if not isinstance(composition, list):
        return False
    
    for comp in composition:
        if not isinstance(comp, dict):
            return False
        if "name" not in comp or "fraction" not in comp:
            return False
    
    return True
