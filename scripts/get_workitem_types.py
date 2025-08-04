#!/usr/bin/env python
"""
Script to retrieve available work item types from Polarion project
"""

import os
import sys
import requests
from pathlib import Path
import json
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}")

# Configuration from environment
base_url = os.getenv('POLARION_BASE_URL')
if not base_url or base_url == 'https://polarion.example.com':
    # Use the correct URL from the test logs
    base_url = 'https://polarion-d.claas.local'

rest_path = os.getenv('POLARION_REST_V1_PATH', '/polarion/rest/v1')
api_url = f"{base_url}{rest_path}"
token = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN', '')
verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'false').lower() == 'true'
project_id = 'Python'  # Use the Python project as shown in the logs

# Suppress SSL warnings if needed
if not verify_ssl:
    warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# Headers
headers = {
    'Authorization': f'Bearer {token}',
    'Accept': '*/*',
    'Content-Type': 'application/json'
}

def get_project_types():
    """Get work item types for a specific project"""
    url = f"{api_url}/projects/{project_id}/workitemtypes"
    
    print(f"Fetching work item types from: {url}")
    
    response = requests.get(url, headers=headers, verify=verify_ssl)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nWork Item Types in project '{project_id}':")
        print("=" * 50)
        
        if 'data' in data:
            for item_type in data['data']:
                type_id = item_type.get('id', 'N/A')
                attributes = item_type.get('attributes', {})
                name = attributes.get('name', 'N/A')
                print(f"- ID: {type_id}")
                print(f"  Name: {name}")
                if 'description' in attributes:
                    print(f"  Description: {attributes['description']}")
                print()
        else:
            print("No work item types found")
            
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def get_workitem_examples():
    """Get example work items to see their structure"""
    url = f"{api_url}/projects/{project_id}/workitems?page[size]=5"
    
    print(f"\nFetching example work items from: {url}")
    
    response = requests.get(url, headers=headers, verify=verify_ssl)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nExample Work Items:")
        print("=" * 50)
        
        if 'data' in data:
            for item in data['data']:
                item_id = item.get('id', 'N/A')
                attributes = item.get('attributes', {})
                item_type = attributes.get('type', 'N/A')
                title = attributes.get('title', 'N/A')
                print(f"- ID: {item_id}")
                print(f"  Type: {item_type}")
                print(f"  Title: {title}")
                
                # Check for custom fields
                if 'customFields' in attributes:
                    print(f"  Custom Fields: {attributes['customFields']}")
                print()

if __name__ == "__main__":
    if not token:
        print("Error: POLARION_PERSONAL_ACCESS_TOKEN not set in environment")
        print("Please set this in your .env file")
        sys.exit(1)
    
    print(f"Polarion API URL: {api_url}")
    print(f"Project ID: {project_id}")
    print(f"SSL Verification: {verify_ssl}")
    print(f"Token present: {'Yes' if token else 'No'}")
    print()
    
    # Try to get work item types
    get_project_types()
    
    # Get some example work items
    get_workitem_examples()