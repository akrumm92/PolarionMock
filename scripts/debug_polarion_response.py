#!/usr/bin/env python3
"""
Debug script to see raw Polarion API responses
"""

import os
import requests
import urllib3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_polarion_response():
    """Debug raw responses from Polarion API"""
    
    endpoint = os.getenv('POLARION_API_ENDPOINT')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print("=== Polarion API Debug ===\n")
    print(f"Endpoint: {endpoint}")
    print(f"PAT: {pat[:10]}...")
    print(f"SSL Verify: {verify_ssl}\n")
    
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Test base endpoint
    print("1. Testing base endpoint...")
    try:
        response = requests.get(endpoint, headers=headers, timeout=30, verify=verify_ssl)
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
        print(f"   Content Length: {len(response.text)} bytes")
        
        if response.text:
            print(f"\n   Raw response (first 500 chars):")
            print(f"   {response.text[:500]}")
            
            # Check if it's HTML
            if response.text.strip().startswith('<'):
                print("\n   ⚠️  Response appears to be HTML, not JSON!")
                print("   This might be a login page or error page.")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test projects endpoint
    print("\n\n2. Testing /projects endpoint...")
    projects_url = f"{endpoint}/projects"
    try:
        response = requests.get(projects_url, headers=headers, timeout=30, verify=verify_ssl)
        print(f"   URL: {projects_url}")
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
        print(f"   Content Length: {len(response.text)} bytes")
        
        if response.text:
            print(f"\n   Raw response (first 500 chars):")
            print(f"   {response.text[:500]}")
            
            # Try to identify format
            if response.text.strip().startswith('<'):
                print("\n   ⚠️  Response is HTML")
            elif response.text.strip().startswith('{'):
                print("\n   Response appears to be JSON")
                try:
                    data = response.json()
                    print(f"   JSON type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())}")
                except:
                    print("   But failed to parse as JSON!")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test with different Accept headers
    print("\n\n3. Testing with different Accept headers...")
    accept_headers = [
        "application/json",
        "application/vnd.api+json", 
        "text/html",
        "*/*"
    ]
    
    for accept in accept_headers:
        print(f"\n   Accept: {accept}")
        test_headers = headers.copy()
        test_headers['Accept'] = accept
        
        try:
            response = requests.get(projects_url, headers=test_headers, timeout=10, verify=verify_ssl)
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
            if response.status_code == 200:
                print(f"   ✅ Success with this Accept header!")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    debug_polarion_response()