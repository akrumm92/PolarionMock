#!/usr/bin/env python
"""
Test script to understand customFields format in Polarion
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

# Configuration
base_url = 'https://polarion-d.claas.local'  # From test logs
rest_path = '/polarion/rest/v1'
api_url = f"{base_url}{rest_path}"
token = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN', '')
verify_ssl = False
project_id = 'Python'

# Suppress SSL warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# Headers
headers = {
    'Authorization': f'Bearer {token}',
    'Accept': '*/*',
    'Content-Type': 'application/json'
}

def test_customfields_formats():
    """Test different customFields formats"""
    import time
    timestamp = int(time.time())
    
    tests = [
        {
            "name": "customFields as empty string",
            "customFields": ""
        },
        {
            "name": "customFields as JSON string",
            "customFields": '{"asil": "ASIL-D", "safetyRelevant": true}'
        },
        {
            "name": "customFields as simple string",
            "customFields": "ASIL-D"
        },
        {
            "name": "No customFields",
            "customFields": None
        }
    ]
    
    for test in tests:
        print(f"\nTesting: {test['name']}")
        print("=" * 50)
        
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": f"CustomFields Test {timestamp} - {test['name']}",
                    "type": "requirement",
                    "description": {
                        "type": "text/html",
                        "value": f"<p>Testing customFields format: {test['name']}</p>"
                    },
                    "priority": "medium",
                    "status": "draft"
                }
            }]
        }
        
        # Add customFields if not None
        if test['customFields'] is not None:
            workitem_data["data"][0]["attributes"]["customFields"] = test['customFields']
        
        url = f"{api_url}/projects/{project_id}/workitems"
        
        try:
            response = requests.post(url, headers=headers, json=workitem_data, verify=verify_ssl)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 201:
                result = response.json()
                created_id = result["data"][0]["id"]
                print(f"SUCCESS! Created: {created_id}")
                
                # Get the created item to see how customFields are stored
                if "/" in created_id:
                    parts = created_id.split("/")
                    get_url = f"{api_url}/projects/{parts[0]}/workitems/{parts[1]}"
                else:
                    get_url = f"{api_url}/projects/{project_id}/workitems/{created_id}"
                
                get_response = requests.get(get_url, headers=headers, verify=verify_ssl)
                if get_response.status_code == 200:
                    item_data = get_response.json()
                    attrs = item_data["data"]["attributes"]
                    if "customFields" in attrs:
                        print(f"CustomFields in response: {attrs['customFields']}")
                    else:
                        print("No customFields in response")
                
                # Clean up - delete the test item
                delete_response = requests.delete(get_url, headers=headers, verify=verify_ssl)
                print(f"Cleanup: {delete_response.status_code}")
                
            else:
                print(f"FAILED: {response.text}")
                
        except Exception as e:
            print(f"ERROR: {e}")
        
        timestamp += 1  # Ensure unique titles

if __name__ == "__main__":
    if not token:
        print("Error: POLARION_PERSONAL_ACCESS_TOKEN not set")
        sys.exit(1)
    
    print(f"Testing customFields formats against: {api_url}")
    print(f"Project: {project_id}")
    print()
    
    test_customfields_formats()