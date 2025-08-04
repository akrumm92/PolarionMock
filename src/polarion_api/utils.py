"""
Utility functions for Polarion API client.
"""

from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlencode
import json
import logging
from pathlib import Path
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Default paths for test data
DEFAULT_INPUT_DIR = Path(__file__).parent / "test_data" / "input"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "test_data" / "output"


def build_query_params(params: Dict[str, Any]) -> str:
    """Build query string from parameters dictionary.
    
    Args:
        params: Dictionary of query parameters
        
    Returns:
        Query string with ? prefix, or empty string if no params
        
    Example:
        >>> build_query_params({"page[size]": 10, "sort": "name"})
        "?page%5Bsize%5D=10&sort=name"
    """
    if not params:
        return ""
    
    # Remove None values
    cleaned_params = {k: v for k, v in params.items() if v is not None}
    
    if not cleaned_params:
        return ""
    
    # Handle special cases
    processed_params = {}
    for key, value in cleaned_params.items():
        if isinstance(value, bool):
            processed_params[key] = str(value).lower()
        elif isinstance(value, (list, tuple)):
            processed_params[key] = ",".join(str(v) for v in value)
        else:
            processed_params[key] = value
    
    return f"?{urlencode(processed_params)}"


def extract_id_parts(resource_id: str) -> Dict[str, str]:
    """Extract parts from a compound resource ID.
    
    Args:
        resource_id: Resource ID (e.g., "project/workitem" or "project/space/document")
        
    Returns:
        Dictionary with extracted parts
        
    Example:
        >>> extract_id_parts("myproject/REQ-123")
        {"project_id": "myproject", "item_id": "REQ-123"}
    """
    parts = resource_id.split("/")
    
    if len(parts) == 2:
        # Work item format: project/item
        return {
            "project_id": parts[0],
            "item_id": parts[1]
        }
    elif len(parts) == 3:
        # Document format: project/space/document
        return {
            "project_id": parts[0],
            "space_id": parts[1],
            "document_id": parts[2]
        }
    else:
        # Unknown format, return as is
        return {"id": resource_id}


def format_json_api_request(resource_type: str, attributes: Dict[str, Any],
                           relationships: Optional[Dict[str, Any]] = None,
                           resource_id: Optional[str] = None) -> Dict[str, Any]:
    """Format data for JSON:API request.
    
    Args:
        resource_type: Type of resource (e.g., "workitems")
        attributes: Resource attributes
        relationships: Optional relationships
        resource_id: Optional resource ID (for updates)
        
    Returns:
        Formatted request data
    """
    data = {
        "type": resource_type,
        "attributes": attributes
    }
    
    if resource_id:
        data["id"] = resource_id
    
    if relationships:
        data["relationships"] = relationships
    
    return {"data": [data] if not resource_id else data}


def parse_json_api_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Parse JSON:API response to extract data and included resources.
    
    Args:
        response: Raw JSON:API response
        
    Returns:
        Parsed response with resolved relationships
    """
    if "data" not in response:
        return response
    
    # Build included resource map
    included_map = {}
    if "included" in response:
        for resource in response["included"]:
            key = f"{resource['type']}:{resource['id']}"
            included_map[key] = resource
    
    # Process data (single or collection)
    def resolve_resource(resource: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve relationships in a resource."""
        if "relationships" not in resource:
            return resource
        
        resolved = resource.copy()
        resolved_rels = {}
        
        for rel_name, rel_data in resource["relationships"].items():
            if "data" in rel_data:
                if isinstance(rel_data["data"], dict):
                    # Single relationship
                    key = f"{rel_data['data']['type']}:{rel_data['data']['id']}"
                    if key in included_map:
                        resolved_rels[rel_name] = included_map[key]
                    else:
                        resolved_rels[rel_name] = rel_data["data"]
                elif isinstance(rel_data["data"], list):
                    # Multiple relationships
                    resolved_items = []
                    for item in rel_data["data"]:
                        key = f"{item['type']}:{item['id']}"
                        if key in included_map:
                            resolved_items.append(included_map[key])
                        else:
                            resolved_items.append(item)
                    resolved_rels[rel_name] = resolved_items
        
        if resolved_rels:
            resolved["resolved_relationships"] = resolved_rels
        
        return resolved
    
    # Process main data
    if isinstance(response["data"], list):
        response["data"] = [resolve_resource(r) for r in response["data"]]
    else:
        response["data"] = resolve_resource(response["data"])
    
    return response


def log_api_call(method: str, url: str, request_data: Optional[Dict] = None,
                response_data: Optional[Dict] = None, status_code: Optional[int] = None):
    """Log API call details for debugging.
    
    Args:
        method: HTTP method
        url: Request URL
        request_data: Request body data
        response_data: Response body data
        status_code: HTTP status code
    """
    logger.debug(f"API Call: {method} {url}")
    
    if request_data:
        logger.debug(f"Request: {json.dumps(request_data, indent=2)}")
    
    if status_code:
        logger.debug(f"Response Status: {status_code}")
    
    if response_data:
        # Truncate large responses
        response_str = json.dumps(response_data, indent=2)
        if len(response_str) > 1000:
            response_str = response_str[:1000] + "\n... (truncated)"
        logger.debug(f"Response: {response_str}")


def validate_resource_id(resource_id: str, resource_type: str) -> bool:
    """Validate resource ID format.
    
    Args:
        resource_id: Resource ID to validate
        resource_type: Type of resource
        
    Returns:
        True if valid, False otherwise
    """
    if not resource_id:
        return False
    
    if resource_type == "workitems":
        # Work item IDs should be project/item format
        parts = resource_id.split("/")
        return len(parts) == 2 and all(parts)
    
    elif resource_type == "documents":
        # Document IDs should be project/space/document format
        parts = resource_id.split("/")
        return len(parts) == 3 and all(parts)
    
    elif resource_type == "projects":
        # Project IDs should not contain slashes
        return "/" not in resource_id
    
    return True


def merge_params(*param_dicts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple parameter dictionaries.
    
    Args:
        *param_dicts: Variable number of parameter dictionaries
        
    Returns:
        Merged parameters dictionary
    """
    result = {}
    for params in param_dicts:
        if params:
            result.update(params)
    return result


# File I/O Functions for Test Data

def ensure_output_dir(output_dir: Optional[Path] = None) -> Path:
    """Ensure output directory exists.
    
    Args:
        output_dir: Optional output directory path
        
    Returns:
        Path to output directory
    """
    dir_path = output_dir or DEFAULT_OUTPUT_DIR
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def save_to_output(data: Union[Dict, List], filename: str, 
                  output_dir: Optional[Path] = None,
                  prefix: Optional[str] = None) -> Path:
    """Save data to output JSON file.
    
    Args:
        data: Data to save
        filename: Output filename (without extension)
        output_dir: Optional output directory
        prefix: Optional prefix for filename (e.g., timestamp)
        
    Returns:
        Path to saved file
    """
    output_path = ensure_output_dir(output_dir)
    
    # Add prefix if provided
    if prefix:
        filename = f"{prefix}_{filename}"
    else:
        # Default to timestamp prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
    
    # Ensure .json extension
    if not filename.endswith('.json'):
        filename = f"{filename}.json"
    
    file_path = output_path / filename
    
    # Save with pretty formatting
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Saved output to: {file_path}")
    return file_path


def load_from_input(filename: str, input_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load data from input JSON file.
    
    Args:
        filename: Input filename (with or without .json extension)
        input_dir: Optional input directory
        
    Returns:
        Loaded data
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    input_path = input_dir or DEFAULT_INPUT_DIR
    
    # Ensure .json extension
    if not filename.endswith('.json'):
        filename = f"{filename}.json"
    
    file_path = input_path / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"Loaded input from: {file_path}")
    return data


def list_input_files(pattern: str = "*.json", 
                    input_dir: Optional[Path] = None) -> List[Path]:
    """List available input files.
    
    Args:
        pattern: Glob pattern for files
        input_dir: Optional input directory
        
    Returns:
        List of input file paths
    """
    input_path = input_dir or DEFAULT_INPUT_DIR
    
    if not input_path.exists():
        return []
    
    return sorted(input_path.glob(pattern))


def save_api_response(response_data: Dict[str, Any], 
                     resource_type: str,
                     operation: str,
                     output_dir: Optional[Path] = None) -> Path:
    """Save API response for analysis.
    
    Args:
        response_data: API response data
        resource_type: Type of resource (workitems, documents, etc.)
        operation: Operation performed (get, list, create, etc.)
        output_dir: Optional output directory
        
    Returns:
        Path to saved file
    """
    filename = f"{resource_type}_{operation}_response"
    
    # Add metadata
    wrapped_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "resource_type": resource_type,
            "operation": operation,
            "item_count": len(response_data.get("data", [])) if isinstance(response_data.get("data"), list) else 1
        },
        "response": response_data
    }
    
    return save_to_output(wrapped_data, filename, output_dir)


def load_test_data_batch(resource_type: str, 
                        input_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load all test data for a resource type.
    
    Args:
        resource_type: Type of resource (workitems, documents)
        input_dir: Optional input directory
        
    Returns:
        List of test data items
    """
    input_path = input_dir or DEFAULT_INPUT_DIR
    pattern = f"{resource_type}_*.json"
    
    all_data = []
    for file_path in list_input_files(pattern, input_path):
        try:
            data = load_from_input(file_path.name, input_path.parent)
            if isinstance(data, list):
                all_data.extend(data)
            else:
                all_data.append(data)
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
    
    return all_data


def prepare_test_data(data: Dict[str, Any], 
                     unique_suffix: Optional[str] = None) -> Dict[str, Any]:
    """Prepare test data with unique values.
    
    Args:
        data: Original test data
        unique_suffix: Optional suffix to make data unique
        
    Returns:
        Modified test data
    """
    if not unique_suffix:
        unique_suffix = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
    
    # Deep copy to avoid modifying original
    import copy
    prepared = copy.deepcopy(data)
    
    # Add suffix to title if present
    if "title" in prepared:
        prepared["title"] = f"{prepared['title']} {unique_suffix}"
    
    # Add suffix to name if present
    if "name" in prepared:
        prepared["name"] = f"{prepared['name']}_{unique_suffix}"
    
    # Add suffix to moduleName if present
    if "moduleName" in prepared:
        prepared["moduleName"] = f"{prepared['moduleName']}_{unique_suffix}"
    
    return prepared