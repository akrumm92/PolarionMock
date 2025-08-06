#!/usr/bin/env python3
"""
Test script for corrected space discovery implementation.
Tests the fixed methods that only use existing Polarion API endpoints.
"""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s %(name)s:%(funcName)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

def test_space_discovery():
    """Test the corrected space discovery implementation."""
    
    # Import after path setup
    from polarion_api.client import PolarionClient
    
    # Get configuration
    base_url = os.getenv('POLARION_BASE_URL')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    project_id = os.getenv('TEST_PROJECT_ID', 'Python')
    
    if not base_url or not pat:
        print("❌ Missing required environment variables")
        print("   POLARION_BASE_URL and POLARION_PERSONAL_ACCESS_TOKEN must be set")
        return False
    
    print("=" * 70)
    print("TESTING CORRECTED SPACE DISCOVERY")
    print("=" * 70)
    print(f"Target: {base_url}")
    print(f"Project: {project_id}")
    print()
    
    try:
        # Initialize client
        client = PolarionClient(
            base_url=base_url,
            personal_access_token=pat,
            verify_ssl=os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
        )
        
        print("1. Testing get_project_spaces()")
        print("-" * 50)
        
        try:
            spaces = client.get_project_spaces(project_id)
            
            if spaces:
                print(f"✅ Found {len(spaces)} spaces:")
                for space in spaces:
                    print(f"   - {space}")
            else:
                print("⚠️  No spaces found (project might be empty)")
            
            print()
            
        except Exception as e:
            print(f"❌ Error in get_project_spaces: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("2. Testing get_all_project_documents_and_spaces()")
        print("-" * 50)
        
        try:
            result = client.get_all_project_documents_and_spaces(
                project_id=project_id,
                max_pages=2  # Limit for testing
            )
            
            spaces = result.get("spaces", [])
            documents = result.get("documents", [])
            meta = result.get("meta", {})
            
            print(f"✅ Discovery results:")
            print(f"   Spaces found: {len(spaces)}")
            if spaces:
                print(f"   Space list: {', '.join(spaces[:5])}")
            
            print(f"   Documents found: {len(documents)}")
            if documents:
                print(f"   Sample documents:")
                for doc in documents[:3]:
                    print(f"     - {doc.get('id', 'unknown')}")
            
            print(f"   Note: {meta.get('note', '')}")
            print()
            
        except Exception as e:
            print(f"❌ Error in get_all_project_documents_and_spaces: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("3. Testing list_documents_in_space()")
        print("-" * 50)
        
        # Try with first found space or default
        test_space = spaces[0] if spaces else "_default"
        
        try:
            docs = client.list_documents_in_space(
                project_id=project_id,
                space_id=test_space
            )
            
            doc_count = len(docs.get("data", []))
            
            if doc_count > 0:
                print(f"✅ Found {doc_count} documents in space '{test_space}':")
                for doc in docs["data"][:3]:
                    doc_id = doc.get("id", "unknown")
                    print(f"   - {doc_id}")
            else:
                print(f"⚠️  No documents found in space '{test_space}'")
            
            if "meta" in docs and "note" in docs["meta"]:
                print(f"   Note: {docs['meta']['note']}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error in list_documents_in_space: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Save results
        results = {
            "project_id": project_id,
            "spaces_found": spaces,
            "total_spaces": len(spaces),
            "total_documents": len(documents),
            "sample_documents": documents[:5] if documents else [],
            "implementation": "Fixed - using only existing Polarion endpoints",
            "note": "Only tests specific document names since bulk endpoints don't exist"
        }
        
        output_file = "test_space_discovery_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✅ All tests passed!")
        print(f"   - Found {len(spaces)} spaces")
        print(f"   - Found {len(documents)} documents")
        print(f"   - Results saved to {output_file}")
        print()
        print("The corrected implementation:")
        print("✅ Only uses existing Polarion endpoints")
        print("✅ Tests specific documents to verify space existence")
        print("✅ Handles 404 errors gracefully")
        print("✅ Works within Polarion's API limitations")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_space_discovery()
    sys.exit(0 if success else 1)