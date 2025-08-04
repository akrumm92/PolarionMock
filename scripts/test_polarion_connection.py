#!/usr/bin/env python3
"""
Test script to verify Polarion API connection using Personal Access Token
"""

import os
import sys
import json
import requests
import urllib3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_polarion_connection():
    """Test connection to Polarion REST API using Personal Access Token."""
    
    # Get configuration from environment
    base_url = os.getenv('POLARION_BASE_URL')
    rest_path = os.getenv('POLARION_REST_V1_PATH', '/polarion/rest/v1')
    api_path = os.getenv('POLARION_API_PATH', '/polarion/api')
    
    # For backward compatibility, check old variable too
    if not base_url:
        old_endpoint = os.getenv('POLARION_API_ENDPOINT')
        if old_endpoint:
            print("⚠️  Using deprecated POLARION_API_ENDPOINT. Please update to use POLARION_BASE_URL")
            endpoint = old_endpoint
        else:
            endpoint = None
    else:
        # Use REST v1 endpoint for main tests
        endpoint = f"{base_url}{rest_path}"
    
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    
    if not endpoint:
        print("❌ Error: POLARION_BASE_URL not set in .env file")
        print("   Example: POLARION_BASE_URL=https://polarion.example.com")
        return False
    
    if not pat:
        print("❌ Error: POLARION_PERSONAL_ACCESS_TOKEN not set in .env file")
        print("   Please generate a Personal Access Token in Polarion and add it to .env")
        return False
    
    print(f"🔍 Testing connection to: {endpoint}")
    print(f"🔑 Using Personal Access Token: {pat[:10]}...")
    
    # Check SSL verification setting
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("⚠️  SSL verification disabled")
    
    # Prepare headers with PAT
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': 'application/json',  # Polarion uses standard JSON, not JSON:API
        'Content-Type': 'application/json'
    }
    
    try:
        # Test API root endpoint
        response = requests.get(endpoint, headers=headers, timeout=10, verify=verify_ssl)
        
        if response.status_code == 200:
            print("✅ Successfully connected to Polarion API!")
            
            # Try to get projects
            projects_url = f"{endpoint}/projects"
            projects_response = requests.get(projects_url, headers=headers, timeout=10, verify=verify_ssl)
            
            if projects_response.status_code == 200:
                try:
                    # Check if response has content
                    if not projects_response.text:
                        print("⚠️  Empty response from projects endpoint")
                        return True  # Connection works but no data
                    
                    # Try to parse JSON
                    data = projects_response.json()
                    
                    # Handle different response formats
                    if isinstance(data, dict):
                        if 'data' in data:  # JSON:API format
                            project_count = len(data.get('data', []))
                            print(f"✅ Found {project_count} projects (JSON:API format)")
                            
                            # List first 5 projects
                            if project_count > 0:
                                print("\nFirst projects:")
                                for i, project in enumerate(data['data'][:5]):
                                    project_id = project.get('id', 'Unknown')
                                    project_name = project.get('attributes', {}).get('name', 'Unknown')
                                    print(f"   - {project_id}: {project_name}")
                        else:
                            # Plain JSON format
                            print("✅ Connected successfully (non-JSON:API format)")
                            print(f"   Response keys: {list(data.keys())[:10]}")
                    elif isinstance(data, list):
                        print(f"✅ Found {len(data)} items (array response)")
                    else:
                        print(f"✅ Connected successfully (unexpected format: {type(data)})")
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️  Response is not valid JSON: {e}")
                    print(f"   Response preview: {projects_response.text[:200]}...")
                    # Connection works even if response isn't JSON
                    return True
                except Exception as e:
                    print(f"⚠️  Error processing response: {e}")
                    return True  # Connection works
            else:
                print(f"⚠️  Could not retrieve projects: {projects_response.status_code}")
                print(f"   Response: {projects_response.text[:200]}")
                
        elif response.status_code == 401:
            print("❌ Authentication failed!")
            print("   Please check your Personal Access Token")
            print(f"   Response: {response.text[:200]}")
            return False
        elif response.status_code == 404:
            print("❌ API endpoint not found!")
            print("   Please check the POLARION_API_ENDPOINT URL")
            print(f"   Current endpoint: {endpoint}")
            return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {str(e)}")
        print("   Please check:")
        print("   - Is the Polarion server accessible?")
        print("   - Is the endpoint URL correct?")
        print("   - Are you behind a proxy?")
        return False
    
    return True

if __name__ == "__main__":
    print("=== Polarion API Connection Test ===\n")
    
    success = test_polarion_connection()
    
    if success:
        print("\n✅ All tests passed! Your Polarion configuration is correct.")
    else:
        print("\n❌ Connection test failed. Please check your configuration.")
        print("\nRequired environment variables in .env:")
        print("  POLARION_API_ENDPOINT=https://your-polarion-server.com/polarion/api")
        print("  POLARION_PERSONAL_ACCESS_TOKEN=your-personal-access-token")
        print("  POLARION_VERIFY_SSL=false  # If using self-signed certificates")
    
    sys.exit(0 if success else 1)