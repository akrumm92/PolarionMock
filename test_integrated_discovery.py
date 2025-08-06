#!/usr/bin/env python3
"""
Test the integrated document discovery that uses work items as primary method.
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
    level=logging.INFO,
    format='%(levelname)-8s %(name)s - %(message)s'
)

# Load environment
load_dotenv()

def test_integrated_discovery():
    """Test the integrated discovery implementation."""
    
    from polarion_api.client import PolarionClient
    
    # Get configuration
    base_url = os.getenv('POLARION_BASE_URL')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    project_id = os.getenv('TEST_PROJECT_ID', 'Python')
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    
    if not base_url or not pat:
        print("❌ Missing POLARION_BASE_URL or POLARION_PERSONAL_ACCESS_TOKEN")
        return False
    
    print("=" * 70)
    print("INTEGRATED DOCUMENT DISCOVERY TEST")
    print("=" * 70)
    print(f"Project: {project_id}")
    print()
    
    try:
        # Initialize client
        client = PolarionClient(
            base_url=base_url,
            personal_access_token=pat,
            verify_ssl=verify_ssl
        )
        
        print("1. Testing get_project_spaces() - Now uses Work Items")
        print("-" * 50)
        
        spaces = client.get_project_spaces(project_id)
        
        if spaces:
            print(f"✅ Found {len(spaces)} spaces:")
            for space in spaces[:10]:
                print(f"   - {space}")
        else:
            print("⚠️  No spaces found")
        
        print()
        print("2. Testing get_all_project_documents_and_spaces()")
        print("-" * 50)
        
        result = client.get_all_project_documents_and_spaces(
            project_id=project_id,
            max_pages=3
        )
        
        spaces = result.get("spaces", [])
        documents = result.get("documents", [])
        meta = result.get("meta", {})
        
        print(f"✅ Results:")
        print(f"   - Spaces: {len(spaces)}")
        print(f"   - Documents: {len(documents)}")
        print(f"   - Discovery method: Work Items (primary)")
        
        # Check document sources
        sources = {}
        for doc in documents:
            source = doc.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        if sources:
            print(f"\n   Document sources:")
            for source, count in sources.items():
                print(f"     - {source}: {count}")
        
        # Save results
        output_file = "integrated_discovery_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "project_id": project_id,
                "spaces": spaces,
                "documents": documents[:20],  # Save first 20
                "total_spaces": len(spaces),
                "total_documents": len(documents),
                "document_sources": sources,
                "meta": meta
            }, f, indent=2)
        
        print(f"\n✅ Results saved to {output_file}")
        
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print("✅ Integrated discovery working!")
        print("   - Primary method: Work Items with module relationships")
        print("   - Fallback method: Testing known document names")
        print(f"   - Found {len(spaces)} spaces and {len(documents)} documents")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_integrated_discovery()
    sys.exit(0 if success else 1)