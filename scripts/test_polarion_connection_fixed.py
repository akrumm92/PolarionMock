#!/usr/bin/env python3
"""
Fixed test script for Polarion API connection using Personal Access Token
Addresses common authentication and connection issues
"""

import os
import sys
import requests
from dotenv import load_dotenv
import urllib3

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
    
    # Clean up endpoint
    endpoint = endpoint.rstrip('/')
    
    print(f"🔍 Testing connection to: {endpoint}")
    print(f"🔑 Using Personal Access Token: {pat[:10]}...")
    
    # Check SSL verification setting
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("⚠️  SSL verification disabled")
    
    # Prepare headers - Polarion requires specific headers
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': '*/*',  # Polarion REST API v1 requires wildcard Accept header
        'Content-Type': 'application/json'
    }
    
    # Configure session for potential proxy support
    session = requests.Session()
    
    # Get proxy settings if they exist
    proxies = {}
    if os.getenv('HTTP_PROXY'):
        proxies['http'] = os.getenv('HTTP_PROXY')
    if os.getenv('HTTPS_PROXY'):
        proxies['https'] = os.getenv('HTTPS_PROXY')
    
    if proxies:
        session.proxies.update(proxies)
        print(f"🌐 Using proxy configuration")
    
    try:
        # Test API root endpoint
        print("\n📡 Testing API endpoint...")
        response = session.get(
            endpoint, 
            headers=headers, 
            timeout=30,
            verify=verify_ssl
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Successfully connected to Polarion API!")
            
            # Try to get projects to verify full access
            projects_url = f"{endpoint}/projects"
            print(f"\n📁 Testing projects endpoint: {projects_url}")
            
            projects_response = session.get(
                projects_url, 
                headers=headers, 
                timeout=30,
                verify=verify_ssl
            )
            
            if projects_response.status_code == 200:
                try:
                    data = projects_response.json()
                    if isinstance(data, dict) and 'data' in data:
                        project_count = len(data.get('data', []))
                        print(f"✅ Found {project_count} projects")
                        
                        # List first 5 projects
                        if project_count > 0:
                            print("\nFirst projects:")
                            for i, project in enumerate(data['data'][:5]):
                                project_id = project.get('id', 'Unknown')
                                project_attrs = project.get('attributes', {})
                                project_name = project_attrs.get('name', 'Unknown')
                                print(f"   - {project_id}: {project_name}")
                    else:
                        print("⚠️  Unexpected response format")
                        print(f"   Response: {projects_response.text[:200]}...")
                except Exception as e:
                    print(f"⚠️  Error parsing response: {e}")
                    print(f"   Response: {projects_response.text[:200]}...")
            else:
                print(f"⚠️  Could not retrieve projects: {projects_response.status_code}")
                if projects_response.text:
                    print(f"   Response: {projects_response.text[:200]}...")
                
        elif response.status_code == 401:
            print("❌ Authentication failed!")
            print("   Possible causes:")
            print("   - Personal Access Token is invalid or expired")
            print("   - Token doesn't have necessary permissions")
            print("   - Wrong authentication format (check if Polarion uses different auth method)")
            
            # Check response headers for authentication hints
            if 'WWW-Authenticate' in response.headers:
                print(f"   Server expects: {response.headers['WWW-Authenticate']}")
            
            if response.text:
                print(f"   Response: {response.text[:200]}...")
            return False
            
        elif response.status_code == 404:
            print("❌ API endpoint not found!")
            print("   Please verify the POLARION_API_ENDPOINT URL")
            print("   Common formats:")
            print("   - https://polarion.example.com/polarion/rest/v1")
            print("   - https://polarion.example.com/polarion/rest/default")
            print(f"   Current: {endpoint}")
            return False
            
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            if response.text:
                print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL Certificate Error: {str(e)}")
        print("\n   Solutions:")
        print("   1. Add POLARION_VERIFY_SSL=false to .env file (for self-signed certificates)")
        print("   2. Install the certificate in your system's trust store")
        print("   3. Use the certificate bundle path if available")
        return False
        
    except requests.exceptions.ProxyError as e:
        print(f"❌ Proxy Error: {str(e)}")
        print("\n   Check your proxy settings:")
        print("   - HTTP_PROXY=http://proxy.example.com:8080")
        print("   - HTTPS_PROXY=http://proxy.example.com:8080")
        print("   - NO_PROXY=localhost,127.0.0.1")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {str(e)}")
        print("\n   Please check:")
        print("   - Is the Polarion server accessible from your network?")
        print("   - Is the endpoint URL correct?")
        print("   - Are you behind a firewall or VPN?")
        print("   - Try pinging the server or accessing it via browser")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out!")
        print("   The server took too long to respond.")
        print("   This might indicate network issues or server problems.")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("=== Polarion API Connection Test ===\n")
    
    success = test_polarion_connection()
    
    if success:
        print("\n✅ All tests passed! Your Polarion configuration is correct.")
    else:
        print("\n❌ Connection test failed. Please check your configuration.")
        print("\nTroubleshooting checklist:")
        print("☐ Verify POLARION_API_ENDPOINT is correct")
        print("☐ Ensure Personal Access Token is valid and not expired")
        print("☐ Check token permissions in Polarion (needs REST API access)")
        print("☐ For SSL issues, try POLARION_VERIFY_SSL=false")
        print("☐ For proxy issues, set HTTP_PROXY and HTTPS_PROXY")
        print("☐ Test network connectivity to Polarion server")
        print("☐ Verify Polarion REST API is enabled on the server")
    
    sys.exit(0 if success else 1)