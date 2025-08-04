#!/usr/bin/env python3
"""
Diagnostic script to identify Polarion connection issues
"""

import os
import sys
import requests
from dotenv import load_dotenv
import urllib3
import socket
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def diagnose_connection():
    """Run diagnostic tests for Polarion connection."""
    
    endpoint = os.getenv('POLARION_API_ENDPOINT')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    
    print("=== Polarion Connection Diagnostics ===\n")
    
    # 1. Check environment variables
    print("1. Environment Variables:")
    print(f"   POLARION_API_ENDPOINT: {'✅ Set' if endpoint else '❌ Not set'}")
    print(f"   POLARION_PERSONAL_ACCESS_TOKEN: {'✅ Set' if pat else '❌ Not set'}")
    
    if not endpoint or not pat:
        print("\n❌ Missing required environment variables!")
        return
    
    # 2. Parse and validate URL
    print("\n2. URL Analysis:")
    parsed = urlparse(endpoint)
    print(f"   Protocol: {parsed.scheme}")
    print(f"   Host: {parsed.hostname}")
    print(f"   Port: {parsed.port or 'default'}")
    print(f"   Path: {parsed.path}")
    
    # 3. DNS resolution
    print("\n3. DNS Resolution:")
    try:
        ip = socket.gethostbyname(parsed.hostname)
        print(f"   ✅ {parsed.hostname} resolves to {ip}")
    except socket.gaierror as e:
        print(f"   ❌ Cannot resolve hostname: {e}")
        return
    
    # 4. Network connectivity
    print("\n4. Network Connectivity:")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            print(f"   ✅ Can connect to {ip}:{port}")
        else:
            print(f"   ❌ Cannot connect to {ip}:{port}")
            return
    except Exception as e:
        print(f"   ❌ Connection test failed: {e}")
        return
    
    # 5. SSL Certificate check (if HTTPS)
    if parsed.scheme == 'https':
        print("\n5. SSL Certificate:")
        
        # First try with SSL verification
        try:
            response = requests.get(endpoint, timeout=10, verify=True)
            print("   ✅ SSL certificate is valid")
        except requests.exceptions.SSLError as e:
            print("   ⚠️  SSL certificate issue (might be self-signed)")
            print(f"   Error: {str(e)[:100]}...")
            
            # Try without SSL verification
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            try:
                response = requests.get(endpoint, timeout=10, verify=False)
                print("   ✅ Connection works without SSL verification")
                print("   💡 Add POLARION_VERIFY_SSL=false to .env file")
            except Exception as e2:
                print(f"   ❌ Still fails without SSL verification: {e2}")
    
    # 6. HTTP Request Tests
    print("\n6. HTTP Request Tests:")
    
    # Disable SSL warnings for testing
    verify = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Test without authentication first
    print("\n   a) Without authentication:")
    try:
        response = requests.get(endpoint, timeout=10, verify=verify)
        print(f"      Response code: {response.status_code}")
        print(f"      Expected: 401 (Unauthorized)")
        
        if response.status_code != 401:
            print(f"      ⚠️  Unexpected response without auth")
            print(f"      Headers: {dict(response.headers)}")
    except Exception as e:
        print(f"      ❌ Request failed: {e}")
    
    # Test with Bearer token
    print("\n   b) With Bearer token:")
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': 'application/vnd.api+json'
    }
    try:
        response = requests.get(endpoint, headers=headers, timeout=10, verify=verify)
        print(f"      Response code: {response.status_code}")
        
        if response.status_code == 200:
            print("      ✅ Authentication successful with Bearer token!")
        elif response.status_code == 401:
            print("      ❌ Authentication failed - check PAT validity")
            if 'WWW-Authenticate' in response.headers:
                print(f"      Auth challenge: {response.headers['WWW-Authenticate']}")
        else:
            print(f"      ⚠️  Unexpected response: {response.status_code}")
            print(f"      Body preview: {response.text[:200]}...")
    except Exception as e:
        print(f"      ❌ Request failed: {e}")
    
    # 7. Proxy check
    print("\n7. Proxy Configuration:")
    http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
    no_proxy = os.getenv('NO_PROXY') or os.getenv('no_proxy')
    
    if http_proxy or https_proxy:
        print(f"   HTTP_PROXY: {http_proxy or 'Not set'}")
        print(f"   HTTPS_PROXY: {https_proxy or 'Not set'}")
        print(f"   NO_PROXY: {no_proxy or 'Not set'}")
        
        # Check if Polarion host should bypass proxy
        if no_proxy and parsed.hostname:
            if parsed.hostname in no_proxy:
                print(f"   ✅ {parsed.hostname} is in NO_PROXY list")
            else:
                print(f"   ⚠️  {parsed.hostname} will use proxy")
    else:
        print("   No proxy configured")
    
    # 8. Summary and recommendations
    print("\n8. Recommendations:")
    print("   - Ensure PAT is generated in Polarion and not expired")
    print("   - PAT should have necessary permissions (read API access)")
    print("   - If behind corporate firewall, check proxy settings")
    print("   - For self-signed certificates, set POLARION_VERIFY_SSL=false")
    print("   - Verify the API endpoint format matches Polarion version")

if __name__ == "__main__":
    diagnose_connection()