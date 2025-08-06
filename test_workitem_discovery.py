#!/usr/bin/env python3
"""
Test document and space discovery via Work Items.
This approach uses the existing /projects/{projectId}/workitems endpoint
to discover documents through module relationships.
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
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

def test_workitem_discovery():
    """Test document discovery via work items."""
    
    # Import after path setup
    from polarion_api.client import PolarionClient
    from polarion_api.documents_via_workitems import DocumentDiscoveryViaWorkItems
    
    # Get configuration
    base_url = os.getenv('POLARION_BASE_URL')
    pat = os.getenv('POLARION_PERSONAL_ACCESS_TOKEN')
    project_id = os.getenv('TEST_PROJECT_ID', 'Python')
    verify_ssl = os.getenv('POLARION_VERIFY_SSL', 'true').lower() != 'false'
    
    if not base_url or not pat:
        print("❌ Missing required environment variables")
        print("   POLARION_BASE_URL and POLARION_PERSONAL_ACCESS_TOKEN must be set")
        return False
    
    print("=" * 70)
    print("DOCUMENT DISCOVERY VIA WORK ITEMS")
    print("=" * 70)
    print(f"Target: {base_url}")
    print(f"Project: {project_id}")
    print()
    
    try:
        # Initialize client
        client = PolarionClient(
            base_url=base_url,
            personal_access_token=pat,
            verify_ssl=verify_ssl
        )
        
        print("1. Testing Work Items Endpoint")
        print("-" * 50)
        
        # First, test if we can get work items
        try:
            test_params = {
                "page[size]": 5,
                "page[number]": 1
            }
            
            test_response = client.get_work_items(
                project_id=project_id,
                **test_params
            )
            
            work_items = test_response.get("data", [])
            print(f"✅ Work items endpoint works. Found {len(work_items)} work items")
            
            # Check if any have module relationships
            has_module = False
            for wi in work_items:
                if "relationships" in wi and "module" in wi.get("relationships", {}):
                    has_module = True
                    break
            
            if has_module:
                print("✅ Found work items with module relationships")
            else:
                print("⚠️  No module relationships found in sample")
            
        except Exception as e:
            print(f"❌ Error accessing work items: {e}")
            return False
        
        print()
        print("2. Discovering Documents via Work Items")
        print("-" * 50)
        
        # Create discoverer
        discoverer = DocumentDiscoveryViaWorkItems(client)
        
        # Run discovery
        try:
            result = discoverer.discover_all_documents_and_spaces(
                project_id=project_id,
                max_pages=5  # Limit for testing
            )
            
            spaces = result.get("spaces", [])
            documents = result.get("documents", [])
            work_items_count = result.get("work_items_count", 0)
            meta = result.get("meta", {})
            
            print(f"✅ Discovery completed:")
            print(f"   - Work items processed: {work_items_count}")
            print(f"   - Documents found: {len(documents)}")
            print(f"   - Spaces found: {len(spaces)}")
            print()
            
            if spaces:
                print(f"   Spaces discovered:")
                for space in spaces[:10]:  # Show first 10
                    print(f"     - {space}")
            
            if documents:
                print(f"\n   Sample documents:")
                for doc in documents[:5]:  # Show first 5
                    print(f"     - {doc}")
            
            print(f"\n   Note: {meta.get('note', '')}")
            
        except Exception as e:
            print(f"❌ Error during discovery: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print()
        print("3. Testing Document Details Retrieval")
        print("-" * 50)
        
        if documents:
            # Try to get details for first few documents
            sample_docs = documents[:3]
            
            try:
                doc_details = discoverer.get_document_details(sample_docs)
                
                print(f"✅ Retrieved details for {len(doc_details)} documents:")
                for doc in doc_details:
                    print(f"   - ID: {doc['id']}")
                    print(f"     Space: {doc.get('space_id', 'unknown')}")
                    attrs = doc.get('attributes', {})
                    if 'title' in attrs:
                        print(f"     Title: {attrs['title']}")
                    
            except Exception as e:
                print(f"⚠️  Could not retrieve document details: {e}")
        
        # Save results
        results = {
            "project_id": project_id,
            "discovery_method": "work_items_module_relationship",
            "spaces_found": spaces,
            "documents_found": documents[:20] if documents else [],  # Save first 20
            "total_spaces": len(spaces),
            "total_documents": len(documents),
            "work_items_processed": work_items_count,
            "meta": meta
        }
        
        output_file = "workitem_discovery_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        if spaces and documents:
            print("✅ SUCCESS! Discovery via Work Items works!")
            print(f"   - Found {len(spaces)} spaces")
            print(f"   - Found {len(documents)} documents")
            print(f"   - Results saved to {output_file}")
            print()
            print("Important notes:")
            print("   - Only documents containing work items are discovered")
            print("   - Empty documents won't be found with this method")
            print("   - This is a workaround for missing /documents endpoint")
            return True
        else:
            print("⚠️  No documents or spaces found")
            print("   Possible reasons:")
            print("   - No work items in the project")
            print("   - Work items don't have module relationships")
            print("   - Need to check query syntax")
            return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_workitem_discovery()
    sys.exit(0 if success else 1)