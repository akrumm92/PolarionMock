"""
Response padding middleware to simulate Polarion's consistent response sizes.
"""

import json
import logging
from flask import Response, request

logger = logging.getLogger(__name__)

# Target size for empty responses (based on Polarion observation)
TARGET_EMPTY_RESPONSE_SIZE = 2472


def pad_response_middleware(response: Response) -> Response:
    """
    Add padding to responses to simulate Polarion's consistent response sizes.
    
    According to POLARION_API_SPECIFICATION.md:
    - Most Polarion responses have a size of 2471-2473 bytes
    - This is especially true for empty responses
    """
    # Only process JSON responses from REST API
    if (not request.path.startswith('/polarion/rest/v1') or 
        response.content_type != 'application/json'):
        return response
    
    try:
        # Get current response data
        data = response.get_json()
        
        # Check if this is an "empty" collection response
        if (data and 
            isinstance(data.get('data'), list) and 
            len(data.get('data')) == 0 and
            data.get('meta', {}).get('totalCount') == 0):
            
            # Calculate current size
            current_json = json.dumps(data, separators=(',', ':'))
            current_size = len(current_json.encode('utf-8'))
            
            # If response is smaller than target, add padding
            if current_size < TARGET_EMPTY_RESPONSE_SIZE:
                padding_needed = TARGET_EMPTY_RESPONSE_SIZE - current_size - 20  # Account for JSON structure
                
                # Add padding as a hidden meta field
                if 'meta' not in data:
                    data['meta'] = {}
                
                # Add padding that won't affect functionality but increases size
                data['meta']['_padding'] = ' ' * padding_needed
                
                # Update response
                response.data = json.dumps(data, separators=(',', ':'))
                
                logger.debug(f"Padded response from {current_size} to ~{TARGET_EMPTY_RESPONSE_SIZE} bytes")
    
    except Exception as e:
        # Don't break responses if padding fails
        logger.error(f"Error padding response: {e}")
    
    return response