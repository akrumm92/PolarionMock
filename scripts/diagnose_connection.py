#!/usr/bin/env python3
"""
Diagnose-Skript für Polarion-Verbindungsprobleme.
Prüft DNS, Netzwerk und API-Konfiguration.
"""

import os
import sys
import socket
import subprocess
import requests
import urllib3
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path.cwd() / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️  No .env file found at: {env_path}")

def check_dns(hostname):
    """Check if hostname can be resolved."""
    print(f"\n1. DNS Resolution Check for: {hostname}")
    print("-" * 50)
    
    try:
        # Try to resolve hostname
        ip_address = socket.gethostbyname(hostname)
        print(f"✅ DNS resolution successful: {hostname} -> {ip_address}")
        
        # Try to get all IPs
        ips = socket.gethostbyname_ex(hostname)
        print(f"   All IPs: {ips[2]}")
        return True
        
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        print("\n   Possible solutions:")
        print("   a) Add to hosts file:")
        print(f"      Windows: C:\\Windows\\System32\\drivers\\etc\\hosts")
        print(f"      Linux/Mac: /etc/hosts")
        print(f"      Add line: <IP_ADDRESS> {hostname}")
        print("\n   b) Check VPN connection if Polarion is in internal network")
        print("\n   c) Use IP address directly in POLARION_BASE_URL")
        return False

def check_network_connectivity(hostname, port=443):
    """Check if we can establish a TCP connection."""
    print(f"\n2. Network Connectivity Check to {hostname}:{port}")
    print("-" * 50)
    
    try:
        # Create a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Try to connect
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"✅ TCP connection successful to {hostname}:{port}")
            return True
        else:
            print(f"❌ Cannot connect to {hostname}:{port} (Error code: {result})")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def check_ping(hostname):
    """Try to ping the host."""
    print(f"\n3. Ping Test to {hostname}")
    print("-" * 50)
    
    try:
        # Platform-specific ping command
        param = '-n' if sys.platform.startswith('win') else '-c'
        command = ['ping', param, '1', hostname]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print(f"✅ Ping successful")
            # Show first few lines of output
            lines = result.stdout.split('\n')[:3]
            for line in lines:
                if line.strip():
                    print(f"   {line}")
            return True
        else:
            print(f"❌ Ping failed")
            if "could not find host" in result.stdout.lower() or "unknown host" in result.stdout.lower():
                print("   Host not found - DNS issue")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Ping timeout")
        return False
    except Exception as e:
        print(f"⚠️  Could not run ping: {e}")
        return None

def check_api_endpoint(base_url, pat):
    """Try to connect to the API endpoint."""
    print(f"\n4. API Endpoint Check")
    print("-" * 50)
    
    if not pat:
        print("⚠️  No Personal Access Token configured")
        return False
    
    # Disable SSL warnings if needed
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    endpoints = [
        f"{base_url}/polarion/rest/v1",
        f"{base_url}/polarion/api",
        f"{base_url}/polarion/rest/projects"
    ]
    
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': '*/*',
        'Content-Type': 'application/json'
    }
    
    successful = False
    for endpoint in endpoints:
        try:
            print(f"\n   Testing: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10, verify=verify_ssl)
            
            if response.status_code == 200:
                print(f"   ✅ Success (200 OK)")
                successful = True
            elif response.status_code == 401:
                print(f"   ⚠️  Authentication failed (401) - Check PAT")
            elif response.status_code == 404:
                print(f"   ⚠️  Endpoint not found (404)")
            else:
                print(f"   ⚠️  Response: {response.status_code}")
                
        except requests.exceptions.ConnectTimeout:
            print(f"   ❌ Connection timeout")
        except requests.exceptions.SSLError as e:
            print(f"   ❌ SSL Error: {e}")
            print(f"      Try setting POLARION_VERIFY_SSL=false")
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ Connection error: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return successful

def check_environment_variables():
    """Check if all required environment variables are set."""
    print("\n5. Environment Variables Check")
    print("-" * 50)
    
    required_vars = {
        'POLARION_BASE_URL': 'Base URL of Polarion server',
        'POLARION_PERSONAL_ACCESS_TOKEN': 'Personal Access Token for authentication',
    }
    
    optional_vars = {
        'POLARION_REST_V1_PATH': 'Path to REST API v1 (default: /polarion/rest/v1)',
        'POLARION_API_PATH': 'Path to legacy API (default: /polarion/api)',
        'POLARION_VERIFY_SSL': 'SSL verification (default: true)',
        'POLARION_ENV': 'Environment (mock/production)',
        'TEST_PROJECT_ID': 'Test project ID'
    }
    
    all_good = True
    
    print("\nRequired variables:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            if var == 'POLARION_PERSONAL_ACCESS_TOKEN':
                print(f"  ✅ {var}: {value[:10]}... ({desc})")
            else:
                print(f"  ✅ {var}: {value} ({desc})")
        else:
            print(f"  ❌ {var}: NOT SET ({desc})")
            all_good = False
    
    print("\nOptional variables:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value} ({desc})")
        else:
            print(f"  ⚠️  {var}: not set ({desc})")
    
    return all_good

def main():
    """Run all diagnostic checks."""
    print("=" * 70)
    print("POLARION CONNECTION DIAGNOSTICS")
    print("=" * 70)
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    if not env_ok:
        print("\n❌ Missing required environment variables!")
        print("Please configure your .env file first.")
        return False
    
    # Get configuration
    base_url = os.getenv('POLARION_BASE_URL')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    
    if not base_url:
        print("\n❌ POLARION_BASE_URL not configured!")
        return False
    
    # Extract hostname from URL
    if base_url.startswith('http://') or base_url.startswith('https://'):
        hostname = base_url.split('://')[1].split('/')[0].split(':')[0]
    else:
        hostname = base_url.split('/')[0].split(':')[0]
    
    print(f"\nTarget server: {hostname}")
    print(f"Base URL: {base_url}")
    
    # Run checks
    dns_ok = check_dns(hostname)
    
    if dns_ok:
        ping_ok = check_ping(hostname)
        net_ok = check_network_connectivity(hostname)
        
        if net_ok:
            api_ok = check_api_endpoint(base_url, pat)
        else:
            api_ok = False
    else:
        ping_ok = False
        net_ok = False
        api_ok = False
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if dns_ok and net_ok and api_ok:
        print("✅ All checks passed! Connection to Polarion should work.")
    else:
        print("❌ Some checks failed. Please address the issues above.")
        
        if not dns_ok:
            print("\n📝 DNS Resolution Issue:")
            print("   The hostname cannot be resolved. Solutions:")
            print("   1. Add entry to hosts file")
            print("   2. Connect to VPN if Polarion is internal")
            print("   3. Use IP address instead of hostname")
            
        elif not net_ok:
            print("\n📝 Network Connectivity Issue:")
            print("   Cannot reach the server. Check:")
            print("   1. Firewall settings")
            print("   2. VPN connection")
            print("   3. Server is running")
            
        elif not api_ok:
            print("\n📝 API Access Issue:")
            print("   Cannot access API. Check:")
            print("   1. Personal Access Token is valid")
            print("   2. REST API is enabled in Polarion")
            print("   3. Correct API paths in configuration")
    
    return dns_ok and net_ok and api_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)