#!/usr/bin/env python3
"""
Comprehensive Polarion connection test that tries multiple endpoint and header combinations
"""

import os
import sys
import requests
import urllib3
from dotenv import load_dotenv
from urllib.parse import urljoin, urlparse

# Load environment variables
load_dotenv()

def test_endpoint_variations():
    """Test various endpoint and header combinations"""
    
    # Get configuration
    base_endpoint = os.getenv('POLARION_API_ENDPOINT')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    
    if not base_endpoint or not pat:
        print("❌ Missing POLARION_API_ENDPOINT or POLARION_PERSONAL_ACCESS_TOKEN")
        return False
    
    # SSL verification
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print(f"🔍 Testing Polarion at: {base_endpoint}")
    print(f"🔑 Using PAT: {pat[:10]}...")
    print(f"🔒 SSL Verification: {verify_ssl}")
    print()
    
    # Parse base URL to construct variations
    parsed = urlparse(base_endpoint)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Different endpoint patterns to try
    endpoint_patterns = [
        # Original endpoint as provided
        (base_endpoint, "Original endpoint"),
        
        # Try /api/ pattern (from working client)
        (urljoin(base_url, "/api/projects"), "/api/projects pattern"),
        
        # Try without /v1
        (base_endpoint.replace('/v1', ''), "Without /v1"),
        
        # Try /polarion/api pattern
        (urljoin(base_url, "/polarion/api/projects"), "/polarion/api pattern"),
        
        # Try legacy patterns
        (urljoin(base_url, "/polarion/rest/default/projects"), "Legacy /rest/default pattern"),
        (urljoin(base_url, "/polarion/ws/rest/v1/projects"), "Legacy /ws/rest pattern"),
    ]
    
    # Different header combinations to try
    header_variations = [
        {
            'name': 'Standard JSON',
            'headers': {
                'Authorization': f'Bearer {pat}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        },
        {
            'name': 'JSON:API format',
            'headers': {
                'Authorization': f'Bearer {pat}',
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json'
            }
        },
        {
            'name': 'Without Content-Type',
            'headers': {
                'Authorization': f'Bearer {pat}',
                'Accept': 'application/json'
            }
        },
        {
            'name': 'With X-Polarion headers',
            'headers': {
                'Authorization': f'Bearer {pat}',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Polarion-REST-API-Version': '1'
            }
        }
    ]
    
    success_count = 0
    
    # Test each combination
    for endpoint, endpoint_desc in endpoint_patterns:
        print(f"\n📍 Testing endpoint: {endpoint_desc}")
        print(f"   URL: {endpoint}")
        
        for header_var in header_variations:
            print(f"\n   🔧 Headers: {header_var['name']}")
            
            try:
                response = requests.get(
                    endpoint,
                    headers=header_var['headers'],
                    timeout=30,
                    verify=verify_ssl
                )
                
                print(f"      Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("      ✅ SUCCESS!")
                    success_count += 1
                    
                    # Try to parse response
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            if 'data' in data:
                                print(f"      Response type: JSON:API (found 'data' key)")
                            else:
                                print(f"      Response type: Plain JSON")
                                print(f"      Keys: {list(data.keys())[:5]}...")
                    except:
                        print("      Response is not JSON")
                    
                    # Show what worked
                    print(f"\n   🎯 WORKING CONFIGURATION:")
                    print(f"      Endpoint: {endpoint}")
                    print(f"      Headers: {header_var['headers']}")
                    return True
                    
                elif response.status_code == 401:
                    print("      ❌ Authentication failed")
                elif response.status_code == 404:
                    print("      ❌ Not found")
                elif response.status_code == 406:
                    print("      ❌ Not Acceptable (wrong Accept header)")
                else:
                    print(f"      ❌ Error: {response.status_code}")
                    
                # Show response details for debugging
                if response.status_code in [401, 406]:
                    if 'WWW-Authenticate' in response.headers:
                        print(f"      Auth header: {response.headers['WWW-Authenticate']}")
                    if response.text:
                        print(f"      Response: {response.text[:200]}...")
                        
            except requests.exceptions.SSLError:
                print("      ❌ SSL Error - try POLARION_VERIFY_SSL=false")
            except requests.exceptions.ConnectionError:
                print("      ❌ Connection Error - endpoint unreachable")
            except requests.exceptions.Timeout:
                print("      ❌ Timeout")
            except Exception as e:
                print(f"      ❌ Error: {type(e).__name__}: {str(e)}")
    
    return success_count > 0

def check_alternative_auth():
    """Test alternative authentication methods"""
    
    endpoint = os.getenv('POLARION_API_ENDPOINT')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print("\n\n=== Testing Alternative Authentication Methods ===")
    
    # Try different auth patterns
    auth_methods = [
        {
            'name': 'X-Polarion-Token header',
            'headers': {
                'X-Polarion-Token': pat,
                'Accept': 'application/json'
            }
        },
        {
            'name': 'Basic Auth with PAT as password',
            'auth': ('polarion', pat),
            'headers': {
                'Accept': 'application/json'
            }
        },
        {
            'name': 'Token in URL parameter',
            'url_suffix': f'?access_token={pat}',
            'headers': {
                'Accept': 'application/json'
            }
        }
    ]
    
    for method in auth_methods:
        print(f"\n🔐 Testing: {method['name']}")
        
        try:
            url = endpoint + method.get('url_suffix', '')
            kwargs = {
                'timeout': 30,
                'verify': verify_ssl,
                'headers': method.get('headers', {})
            }
            
            if 'auth' in method:
                kwargs['auth'] = method['auth']
            
            response = requests.get(url, **kwargs)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ SUCCESS with this auth method!")
                return True
                
        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}")
    
    return False

if __name__ == "__main__":
    print("=== Comprehensive Polarion Connection Test ===\n")
    
    # Test endpoint variations
    success = test_endpoint_variations()
    
    # If no success, try alternative auth
    if not success:
        success = check_alternative_auth()
    
    if success:
        print("\n\n✅ Found working configuration! Check the output above for details.")
    else:
        print("\n\n❌ Could not connect with any configuration.")
        print("\nPossible issues:")
        print("1. Check if the Polarion REST API is enabled on your server")
        print("2. Verify the Personal Access Token has API access permissions")
        print("3. Check with your Polarion administrator for the correct API endpoint")
        print("4. Some Polarion installations use custom authentication methods")
    
    sys.exit(0 if success else 1)