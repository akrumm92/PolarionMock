#!/usr/bin/env python3
"""
Analyze Polarion Swagger/OpenAPI specification from the live API
Uses Personal Access Token for authentication
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def fetch_swagger_spec():
    """Fetch Swagger/OpenAPI specification from Polarion API."""
    
    endpoint = os.getenv('POLARION_API_ENDPOINT')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    
    if not endpoint or not pat:
        print("❌ Error: Missing configuration")
        print("   Required environment variables:")
        print("   - POLARION_API_ENDPOINT")
        print("   - POLARION_PERSONAL_ACCESS_TOKEN")
        return None
    
    # Headers with Personal Access Token
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': '*/*'  # Polarion requires wildcard Accept header
    }
    
    # Common Swagger/OpenAPI URLs to try
    swagger_urls = [
        f"{endpoint}/swagger.json",
        f"{endpoint}/openapi.json",
        f"{endpoint}/api-docs",
        f"{endpoint}/swagger",
        f"{endpoint}/../swagger-ui/swagger.json",
        f"{endpoint.replace('/rest/v1', '')}/api-docs",
        f"{endpoint.replace('/rest/v1', '')}/swagger.json"
    ]
    
    print(f"🔍 Searching for Swagger/OpenAPI specification...")
    print(f"🔑 Using PAT: {pat[:10]}...")
    
    for url in swagger_urls:
        print(f"\nTrying: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"✅ Found specification at: {url}")
                return response.json()
            else:
                print(f"   ❌ Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Try to get from the API root
    print(f"\nTrying API root: {endpoint}")
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Check if there's a link to the spec
            if 'links' in data:
                for key, value in data['links'].items():
                    if 'swagger' in key.lower() or 'openapi' in key.lower():
                        print(f"Found spec link: {value}")
                        spec_response = requests.get(value, headers=headers, timeout=10)
                        if spec_response.status_code == 200:
                            return spec_response.json()
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    return None

def analyze_spec(spec):
    """Analyze the OpenAPI/Swagger specification."""
    
    print("\n=== API Specification Analysis ===")
    
    # Basic info
    if 'info' in spec:
        info = spec['info']
        print(f"\nAPI Info:")
        print(f"  Title: {info.get('title', 'N/A')}")
        print(f"  Version: {info.get('version', 'N/A')}")
        print(f"  Description: {info.get('description', 'N/A')[:100]}...")
    
    # Count endpoints
    paths = spec.get('paths', {})
    print(f"\nEndpoints: {len(paths)}")
    
    # Group by resource type
    resources = {}
    for path, methods in paths.items():
        # Extract resource type from path
        parts = path.strip('/').split('/')
        if parts:
            resource = parts[0]
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(path)
    
    print(f"\nResources found:")
    for resource, endpoints in sorted(resources.items()):
        print(f"  - {resource}: {len(endpoints)} endpoints")
    
    # List all endpoints
    print(f"\nAll endpoints:")
    for path in sorted(paths.keys()):
        methods = paths[path]
        method_list = [m.upper() for m in methods.keys() if m != 'parameters']
        print(f"  {', '.join(method_list):20} {path}")
    
    return spec

def save_spec(spec):
    """Save the specification to file."""
    
    # Create output directory
    output_dir = Path("Input/api")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    output_file = output_dir / "polarion-openapi.json"
    with open(output_file, 'w') as f:
        json.dump(spec, f, indent=2)
    
    print(f"\n✅ Saved specification to: {output_file}")
    
    # Also save a summary
    summary_file = output_dir / "api-summary.txt"
    with open(summary_file, 'w') as f:
        f.write("=== Polarion API Summary ===\n\n")
        
        if 'info' in spec:
            info = spec['info']
            f.write(f"Title: {info.get('title', 'N/A')}\n")
            f.write(f"Version: {info.get('version', 'N/A')}\n\n")
        
        f.write("Endpoints:\n")
        paths = spec.get('paths', {})
        for path in sorted(paths.keys()):
            methods = paths[path]
            method_list = [m.upper() for m in methods.keys() if m != 'parameters']
            f.write(f"  {', '.join(method_list):20} {path}\n")
    
    print(f"✅ Saved summary to: {summary_file}")

def main():
    """Main function."""
    
    print("=== Polarion Swagger/OpenAPI Analyzer ===\n")
    
    # Fetch specification
    spec = fetch_swagger_spec()
    
    if not spec:
        print("\n❌ Could not find Swagger/OpenAPI specification")
        print("\nPossible reasons:")
        print("1. The Polarion instance doesn't expose OpenAPI/Swagger")
        print("2. The specification is at a different URL")
        print("3. Additional authentication is required")
        print("\nYou can manually place the specification in Input/api/")
        return 1
    
    # Analyze
    analyze_spec(spec)
    
    # Save
    save_spec(spec)
    
    print("\n✅ Analysis complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())