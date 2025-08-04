#!/usr/bin/env python3
"""
Improved test script to verify Polarion API connection using Personal Access Token
Handles common connection issues like SSL certificates, proxies, and authentication formats
"""

import os
import sys
import requests
from dotenv import load_dotenv
import urllib3
import json

# Load environment variables
load_dotenv()

def test_polarion_connection():
    """Test connection to Polarion REST API using Personal Access Token."""
    
    # Get configuration from environment
    endpoint = os.getenv('POLARION_API_ENDPOINT')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    
    if not endpoint:
        print("❌ Error: POLARION_API_ENDPOINT not set in .env file")
        print("   Example: https://polarion.example.com/polarion/rest/v1")
        return False
    
    if not pat:
        print("❌ Error: POLARION_PERSONAL_ACCESS_TOKEN not set in .env file")
        print("   Please generate a Personal Access Token in Polarion and add it to .env")
        return False
    
    # Clean up endpoint - ensure no trailing slash
    endpoint = endpoint.rstrip('/')
    
    print(f"🔍 Testing connection to: {endpoint}")
    print(f"🔑 Using Personal Access Token: {pat[:10]}...")
    
    # Check for proxy settings
    http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
    if http_proxy or https_proxy:
        print(f"🌐 Using proxy: {https_proxy or http_proxy}")
    
    # Prepare session with various authentication methods
    session = requests.Session()
    
    # Disable SSL warnings if needed (for self-signed certificates)
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("⚠️  SSL verification disabled")
    
    # Try different authentication methods
    auth_methods = [
        {
            'name': 'Bearer Token',
            'headers': {
                'Authorization': f'Bearer {pat}',
                'Accept': 'application/vnd.api+json',  # JSON:API format
                'Content-Type': 'application/vnd.api+json'
            }
        },
        {
            'name': 'X-Polarion-Token',
            'headers': {
                'X-Polarion-Token': pat,
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json'
            }
        },
        {
            'name': 'Basic Auth (PAT as password)',
            'auth': ('polarion', pat),
            'headers': {
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json'
            }
        }
    ]
    
    # Test different endpoint variations
    endpoint_variations = [
        endpoint,
        f"{endpoint}/projects",  # Try direct projects endpoint
        endpoint.replace('/rest/v1', '/rest/default/projects'),  # Try legacy format
    ]
    
    for auth_method in auth_methods:
        print(f"\n🔐 Trying authentication method: {auth_method['name']}")
        
        for test_endpoint in endpoint_variations:
            print(f"   Testing endpoint: {test_endpoint}")
            
            try:
                # Prepare request parameters
                request_params = {
                    'timeout': 30,
                    'verify': verify_ssl
                }
                
                # Add headers
                if 'headers' in auth_method:
                    request_params['headers'] = auth_method['headers']
                
                # Add auth if specified
                if 'auth' in auth_method:
                    request_params['auth'] = auth_method['auth']
                
                # Make request
                response = session.get(test_endpoint, **request_params)
                
                print(f"   Response code: {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ Successfully connected!")
                    
                    # Try to parse response
                    try:
                        data = response.json()
                        print(f"   Response type: {type(data)}")
                        
                        # Check if it's JSON:API format
                        if isinstance(data, dict) and 'data' in data:
                            print("   ✅ Valid JSON:API response")
                            if isinstance(data['data'], list):
                                print(f"   Found {len(data['data'])} items")
                            return True
                        else:
                            print(f"   Response preview: {json.dumps(data, indent=2)[:200]}...")
                            
                    except json.JSONDecodeError:
                        print(f"   Response is not JSON: {response.text[:200]}...")
                        
                elif response.status_code == 401:
                    print("   ❌ Authentication failed")
                    print(f"   Response: {response.text[:200]}...")
                    
                elif response.status_code == 403:
                    print("   ❌ Access forbidden - check permissions")
                    
                elif response.status_code == 404:
                    print("   ❌ Endpoint not found")
                    
                else:
                    print(f"   ❌ Unexpected response: {response.status_code}")
                    print(f"   Headers: {dict(response.headers)}")
                    
            except requests.exceptions.SSLError as e:
                print(f"   ❌ SSL Error: {str(e)}")
                print("   Try setting POLARION_VERIFY_SSL=false in .env file")
                
            except requests.exceptions.ProxyError as e:
                print(f"   ❌ Proxy Error: {str(e)}")
                print("   Check your proxy settings")
                
            except requests.exceptions.ConnectionError as e:
                print(f"   ❌ Connection Error: {str(e)}")
                print("   Check if Polarion server is accessible")
                
            except requests.exceptions.Timeout:
                print("   ❌ Request timed out")
                
            except Exception as e:
                print(f"   ❌ Unexpected error: {type(e).__name__}: {str(e)}")
    
    return False

def check_network_connectivity():
    """Basic network connectivity check."""
    print("\n🌐 Checking network connectivity...")
    
    try:
        # Try to reach a public endpoint
        response = requests.get("https://httpbin.org/get", timeout=5)
        if response.status_code == 200:
            print("✅ Internet connection is working")
        else:
            print("⚠️  Internet connection may have issues")
    except Exception as e:
        print(f"❌ No internet connection: {str(e)}")

if __name__ == "__main__":
    print("=== Polarion API Connection Test (Improved) ===\n")
    
    # Check basic connectivity first
    check_network_connectivity()
    
    # Test Polarion connection
    success = test_polarion_connection()
    
    if success:
        print("\n✅ Successfully connected to Polarion!")
    else:
        print("\n❌ Could not connect to Polarion")
        print("\nTroubleshooting steps:")
        print("1. Verify POLARION_API_ENDPOINT is correct")
        print("2. Ensure Personal Access Token is valid and not expired")
        print("3. Check if you need to set proxy environment variables")
        print("4. Try setting POLARION_VERIFY_SSL=false for self-signed certificates")
        print("5. Verify the API endpoint format (e.g., /polarion/rest/v1)")
        print("6. Check Polarion server logs for authentication errors")
        print("\nExample .env configuration:")
        print("  POLARION_API_ENDPOINT=https://polarion.company.com/polarion/rest/v1")
        print("  POLARION_PERSONAL_ACCESS_TOKEN=your-personal-access-token")
        print("  POLARION_VERIFY_SSL=false  # Only if using self-signed certificates")
        print("  HTTPS_PROXY=http://proxy.company.com:8080  # If behind proxy")
    
    sys.exit(0 if success else 1)