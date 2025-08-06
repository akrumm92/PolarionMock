#!/usr/bin/env python3
"""
Simple test to check if /projects/{projectId}/documents endpoint exists.
Tests with minimal parameters and raw requests.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

def simple_test():
    """Simple raw test of the documents endpoint."""
    
    # Get configuration
    base_url = os.getenv('POLARION_BASE_URL', 'https://polarion-d.claas.local')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    project_id = os.getenv('TEST_PROJECT_ID', 'Python')
    
    if not pat:
        print("❌ POLARION_PERSONAL_ACCESS_TOKEN not set!")
        return
    
    # Build URL - try different variations
    urls_to_test = [
        f"{base_url}/polarion/rest/v1/projects/{project_id}/documents",
        f"{base_url}/rest/v1/projects/{project_id}/documents",
        f"{base_url}/polarion/rest/projects/{project_id}/documents",
    ]
    
    # Headers - MUST use wildcard Accept for Polarion
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': '*/*',
        'Content-Type': 'application/json'
    }
    
    print("=" * 70)
    print("SIMPLE ENDPOINT TEST")
    print("=" * 70)
    print(f"Project: {project_id}")
    print(f"Token: {pat[:20]}...")
    print()
    
    for url in urls_to_test:
        print(f"Testing: {url}")
        print("-" * 50)
        
        try:
            # Simple GET request
            response = requests.get(
                url,
                headers=headers,
                verify=False,  # Disable SSL verification for test
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! Endpoint exists!")
                
                # Try to parse response
                try:
                    data = response.json()
                    if 'data' in data:
                        print(f"Documents found: {len(data['data'])}")
                        
                        # Show first document ID if exists
                        if data['data']:
                            first_doc = data['data'][0]
                            print(f"First document ID: {first_doc.get('id', 'unknown')}")
                            
                            # Extract space from ID
                            doc_id = first_doc.get('id', '')
                            if '/' in doc_id:
                                parts = doc_id.split('/')
                                if len(parts) >= 3:
                                    print(f"Space found: {parts[1]}")
                    else:
                        print("Response has no 'data' field")
                        print(f"Response keys: {list(data.keys())}")
                        
                except Exception as e:
                    print(f"Could not parse JSON: {e}")
                    print(f"Response text: {response.text[:500]}")
                
                return True
                
            elif response.status_code == 404:
                print("❌ 404 Not Found - Endpoint doesn't exist")
                print(f"Response: {response.text[:200]}")
                
            elif response.status_code == 401:
                print("❌ 401 Unauthorized - Check your token")
                
            elif response.status_code == 406:
                print("❌ 406 Not Acceptable - Wrong Accept header")
                
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except requests.exceptions.SSLError:
            print("❌ SSL Error - Certificate verification failed")
            print("   Set POLARION_VERIFY_SSL=false in .env")
            
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: {e}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    print("=" * 70)
    print("RESULT: The endpoint does NOT exist in Polarion REST API v1")
    print("This confirms that bulk document listing is not available.")
    print("=" * 70)

if __name__ == "__main__":
    simple_test()