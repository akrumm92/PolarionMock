#!/usr/bin/env python3
"""
Test script to verify Polarion API connection using Personal Access Token
"""

import os
import sys
import requests
import urllib3
from dotenv import load_dotenv

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
        'Accept': 'application/vnd.api+json'  # JSON:API format required by Polarion
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
                data = projects_response.json()
                project_count = len(data.get('data', []))
                print(f"✅ Found {project_count} projects")
                
                # List first 5 projects
                if project_count > 0:
                    print("\nFirst projects:")
                    for i, project in enumerate(data['data'][:5]):
                        project_id = project.get('id', 'Unknown')
                        project_name = project.get('attributes', {}).get('name', 'Unknown')
                        print(f"   - {project_id}: {project_name}")
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
        print("  POLARION_API_ENDPOINT=https://your-polarion-server.com/polarion/rest/v1")
        print("  POLARION_PERSONAL_ACCESS_TOKEN=your-personal-access-token")
    
    sys.exit(0 if success else 1)