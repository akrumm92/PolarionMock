"""
Helper functions for module tests.
"""

import json
import os
from pathlib import Path
from functools import wraps
from typing import Any, Dict, Optional


# Use absolute path to ensure correct location
OUTPUT_DIR = Path(__file__).parent.absolute() / "outputdata"


def save_response_to_json(filename: str, data: Any) -> None:
    """Save API response data to JSON file.
    
    Args:
        filename: Name of the output file (without .json extension)
        data: Response data to save
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    filepath = OUTPUT_DIR / f"{filename}.json"
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_api_response(test_name: str):
    """Decorator to save API responses from test methods.
    
    Args:
        test_name: Name for the output JSON file
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Run the test
            result = func(*args, **kwargs)
            
            # If the test returns a response, save it
            if result is not None:
                save_response_to_json(test_name, result)
            
            return result
        return wrapper
    return decorator


def capture_response(method_name: str, response: Any) -> Any:
    """Capture and save a response from an API call.
    
    Args:
        method_name: Name of the API method (used for filename)
        response: The API response to save
        
    Returns:
        The original response (pass-through)
    """
    if response is not None:
        save_response_to_json(method_name, response)
    return response