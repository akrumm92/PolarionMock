#!/usr/bin/env python3
"""
Test script that uses both Polarion endpoints correctly:
- /polarion/api for authentication testing
- /polarion/rest/v1 for REST API operations
"""

import os
import sys
import json
import requests
import urllib3
from dotenv import load_dotenv
from urllib.parse import urljoin

# Load environment variables
load_dotenv()

def get_endpoints():
    """Get both endpoints from environment variables"""
    base_url = os.getenv('POLARION_BASE_URL')
    rest_v1_path = os.getenv('POLARION_REST_V1_PATH', '/polarion/rest/v1')
    api_path = os.getenv('POLARION_API_PATH', '/polarion/api')
    
    if not base_url:
        print("❌ Error: POLARION_BASE_URL not set in .env file")
        print("   Example: https://polarion.example.com")
        return None, None
    
    # Construct full endpoints
    rest_v1_endpoint = urljoin(base_url, rest_v1_path)
    api_endpoint = urljoin(base_url, api_path)
    
    return rest_v1_endpoint, api_endpoint

def test_authentication(api_endpoint, pat, verify_ssl):
    """Test authentication using the /polarion/api endpoint"""
    print("\n1. Testing Authentication")
    print(f"   Using: {api_endpoint}")
    
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test with /polarion/api/projects
        test_url = f"{api_endpoint}/projects"
        response = requests.get(test_url, headers=headers, timeout=30, verify=verify_ssl)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Authentication successful!")
            return True
        elif response.status_code == 401:
            print("   ❌ Authentication failed - check your PAT")
            return False
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
            return response.status_code < 400
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_rest_api_v1(rest_v1_endpoint, pat, verify_ssl):
    """Test REST API v1 operations"""
    print("\n2. Testing REST API v1")
    print(f"   Using: {rest_v1_endpoint}")
    
    # Try different Accept headers for REST v1
    accept_headers = [
        ('application/vnd.api+json', 'JSON:API format'),
        ('application/json', 'Standard JSON'),
        ('*/*', 'Wildcard')
    ]
    
    for accept_header, description in accept_headers:
        print(f"\n   Trying Accept: {accept_header} ({description})")
        
        headers = {
            'Authorization': f'Bearer {pat}',
            'Accept': accept_header
        }
        
        try:
            # Test root endpoint
            response = requests.get(rest_v1_endpoint, headers=headers, timeout=30, verify=verify_ssl)
            print(f"      Root status: {response.status_code}")
            
            if response.status_code == 200:
                print("      ✅ Success with this Accept header!")
                
                # Test projects endpoint
                projects_url = f"{rest_v1_endpoint}/projects"
                proj_response = requests.get(projects_url, headers=headers, timeout=30, verify=verify_ssl)
                print(f"      Projects status: {proj_response.status_code}")
                
                if proj_response.status_code == 200:
                    try:
                        data = proj_response.json()
                        if isinstance(data, dict) and 'data' in data:
                            print(f"      ✅ Found {len(data['data'])} projects")
                            
                            # Show first project
                            if data['data']:
                                first_project = data['data'][0]
                                print(f"      First project: {first_project.get('id', 'Unknown')}")
                    except:
                        print("      Response is not JSON")
                
                return True, accept_header
                
            elif response.status_code == 406:
                print("      ❌ Not Acceptable")
            elif response.status_code == 401:
                print("      ❌ Unauthorized")
            else:
                print(f"      Status: {response.status_code}")
                
        except Exception as e:
            print(f"      Error: {e}")
    
    return False, None

def main():
    """Main test function"""
    print("=== Polarion Dual Endpoint Test ===")
    
    # Get configuration
    rest_v1_endpoint, api_endpoint = get_endpoints()
    if not rest_v1_endpoint:
        return False
    
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    if not pat:
        print("❌ Error: POLARION_PERSONAL_ACCESS_TOKEN not set in .env file")
        return False
    
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print(f"\n🔍 Configuration:")
    print(f"   Base URL: {os.getenv('POLARION_BASE_URL')}")
    print(f"   REST v1: {rest_v1_endpoint}")
    print(f"   API: {api_endpoint}")
    print(f"   PAT: {pat[:10]}...")
    print(f"   SSL Verify: {verify_ssl}")
    
    # Test authentication with /polarion/api
    auth_success = test_authentication(api_endpoint, pat, verify_ssl)
    
    if not auth_success:
        print("\n❌ Authentication failed. Cannot proceed with API tests.")
        return False
    
    # Test REST API v1
    api_success, working_accept = test_rest_api_v1(rest_v1_endpoint, pat, verify_ssl)
    
    if api_success:
        print(f"\n✅ Successfully connected to Polarion!")
        print(f"\nWorking configuration:")
        print(f"   Authentication: {api_endpoint}")
        print(f"   REST API: {rest_v1_endpoint}")
        print(f"   Accept header: {working_accept}")
        
        # Update .env suggestion
        print(f"\nUpdate your .env file on the other computer:")
        print(f"   POLARION_BASE_URL={os.getenv('POLARION_BASE_URL')}")
        print(f"   POLARION_REST_V1_PATH={os.getenv('POLARION_REST_V1_PATH', '/polarion/rest/v1')}")
        print(f"   POLARION_API_PATH={os.getenv('POLARION_API_PATH', '/polarion/api')}")
        print(f"   POLARION_PERSONAL_ACCESS_TOKEN=your-actual-pat")
        print(f"   POLARION_VERIFY_SSL=false")
        
        return True
    else:
        print("\n❌ Could not connect to REST API v1")
        print("\nPossible issues:")
        print("1. REST API v1 might not be enabled in your Polarion instance")
        print("2. Your PAT might not have REST API permissions")
        print("3. The server might require a specific Accept header we haven't tried")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)