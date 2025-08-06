#!/usr/bin/env python3
"""
Test if the /projects/{projectId}/documents endpoint actually exists.
According to documentation, it SHOULD exist for listing all documents.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_documents_endpoint():
    """Test the documents endpoint with various configurations."""
    
    base_url = os.getenv('POLARION_BASE_URL')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    project_id = os.getenv('TEST_PROJECT_ID', 'Python')
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    
    if not base_url or not pat:
        print("❌ Missing POLARION_BASE_URL or POLARION_PERSONAL_ACCESS_TOKEN")
        return False
    
    print("=" * 70)
    print("TESTING DOCUMENTS ENDPOINT")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"Project: {project_id}")
    print()
    
    # Test different URL patterns
    endpoints_to_test = [
        # Standard REST v1 pattern
        f"{base_url}/polarion/rest/v1/projects/{project_id}/documents",
        # Without v1
        f"{base_url}/polarion/rest/projects/{project_id}/documents",
        # Different path structure
        f"{base_url}/rest/v1/projects/{project_id}/documents",
    ]
    
    # Different Accept headers to test
    accept_headers = [
        "*/*",  # Polarion requires this
        "application/json",
        "application/vnd.api+json"
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\nTesting: {endpoint}")
        print("-" * 50)
        
        for accept in accept_headers:
            headers = {
                'Authorization': f'Bearer {pat}',
                'Accept': accept,
                'Content-Type': 'application/json'
            }
            
            params = {
                'page[size]': 10,
                'page[number]': 1,
                'fields[documents]': 'id,title,type'
            }
            
            try:
                print(f"  Accept header: {accept}")
                response = requests.get(
                    endpoint, 
                    headers=headers, 
                    params=params,
                    verify=verify_ssl,
                    timeout=10
                )
                
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("  ✅ SUCCESS! Endpoint exists")
                    data = response.json()
                    
                    if 'data' in data:
                        doc_count = len(data['data'])
                        print(f"  Found {doc_count} documents")
                        
                        if doc_count > 0:
                            # Extract spaces from document IDs
                            spaces = set()
                            for doc in data['data']:
                                doc_id = doc.get('id', '')
                                if '/' in doc_id:
                                    parts = doc_id.split('/')
                                    if len(parts) >= 3:
                                        spaces.add(parts[1])
                            
                            print(f"  Spaces found: {spaces}")
                    
                    # This is the working configuration!
                    print("\n  🎯 WORKING CONFIGURATION:")
                    print(f"     URL: {endpoint}")
                    print(f"     Accept: {accept}")
                    return True
                    
                elif response.status_code == 404:
                    print(f"  ❌ 404 Not Found")
                    if response.text:
                        print(f"  Response: {response.text[:200]}")
                        
                elif response.status_code == 406:
                    print(f"  ❌ 406 Not Acceptable (wrong Accept header)")
                    
                elif response.status_code == 401:
                    print(f"  ❌ 401 Unauthorized")
                    
                else:
                    print(f"  ❌ Status {response.status_code}")
                    if response.text:
                        print(f"  Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("❌ The /projects/{projectId}/documents endpoint does NOT exist")
    print("   This confirms that Polarion REST API v1 has no bulk document listing")
    print("\n   Alternative approaches needed:")
    print("   1. Use work items with moduleURI to find documents")
    print("   2. Query specific document IDs if known")
    print("   3. Use SOAP API if available")
    
    return False

if __name__ == "__main__":
    success = test_documents_endpoint()
    sys.exit(0 if success else 1)