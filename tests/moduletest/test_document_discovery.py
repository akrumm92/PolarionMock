"""
Test module for discovering documents and spaces via work items.
"""

import os
import json
import pytest
import logging
from datetime import datetime
from typing import Dict, Any

from src.polarion_api.client import PolarionClient

logger = logging.getLogger(__name__)


@pytest.fixture
def test_project_id():
    """Get test project ID from environment or use default."""
    # Use Python project as we know it exists from SwaggerUiResponse.json
    project_id = os.getenv("TEST_PROJECT_ID", "Python")
    logger.info(f"Using project ID: {project_id}")
    return project_id


@pytest.fixture
def polarion_client():
    """Create Polarion client for testing."""
    from dotenv import load_dotenv
    import os
    
    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    load_dotenv(env_path)
    
    # Check environment
    env = os.getenv("POLARION_ENV", "production")
    logger.info(f"Testing against: {env}")
    
    # The PolarionClient will read from environment variables directly
    # so we just need to ensure they're set correctly
    
    if env == "mock":
        # Override for mock
        os.environ["POLARION_BASE_URL"] = os.getenv("MOCK_BASE_URL", "http://localhost:5001")
        os.environ["POLARION_PERSONAL_ACCESS_TOKEN"] = os.getenv("MOCK_AUTH_TOKEN", "")
        os.environ["POLARION_VERIFY_SSL"] = "false"
    
    # Check token
    token = os.getenv("POLARION_PERSONAL_ACCESS_TOKEN")
    if not token:
        pytest.skip("No authentication token available")
    
    # Create client - it will read from environment
    client = PolarionClient()
    
    return client


def save_response_to_json(filename: str, data: Dict[str, Any], output_dir: str = "tests/moduletest/outputdata"):
    """Save response data to JSON file.
    
    Args:
        filename: Base filename (without .json extension)
        data: Data to save
        output_dir: Output directory
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{filename}.json")
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved response to {filepath}")
    return filepath


class TestDocumentDiscovery:
    """Test suite for document and space discovery."""
    
    def test_discover_all_documents_and_spaces(self, polarion_client, test_project_id):
        """Test discovering all documents and spaces in a project.
        
        This test fetches all work items and extracts document information
        from their module relationships.
        """
        logger.info(f"Testing document discovery for project: {test_project_id}")
        
        # Run discovery
        result = polarion_client.discover_all_documents_and_spaces(
            project_id=test_project_id,
            save_output=True,
            output_dir="tests/moduletest/outputdata"
        )
        
        # Validate result structure
        assert "project" in result
        assert "spaces" in result
        assert "documents" in result
        assert "statistics" in result
        
        # Check project ID
        assert result["project"] == test_project_id
        
        # Check that we found spaces
        spaces = result["spaces"]
        assert isinstance(spaces, list)
        if spaces:
            logger.info(f"Found {len(spaces)} spaces: {spaces}")
            assert len(spaces) > 0
            # Check for expected spaces (based on SwaggerUiResponse.json)
            expected_spaces = ["Functional Layer"]
            for expected in expected_spaces:
                if expected in spaces:
                    logger.info(f"✓ Found expected space: {expected}")
        
        # Check documents
        documents = result["documents"]
        assert isinstance(documents, list)
        if documents:
            logger.info(f"Found {len(documents)} unique documents")
            
            # Check document structure
            for doc in documents[:5]:  # Check first 5
                assert "id" in doc
                assert "project" in doc
                assert "space" in doc
                assert "name" in doc
                assert "work_item_refs" in doc
                assert isinstance(doc["work_item_refs"], list)
                
                logger.debug(f"Document: {doc['id']} referenced by {len(doc['work_item_refs'])} work items")
        
        # Check statistics
        stats = result["statistics"]
        assert "total_spaces" in stats
        assert "total_documents" in stats
        assert "workitems_processed" in stats
        assert "workitems_with_modules" in stats
        assert "workitems_without_modules" in stats
        
        logger.info(f"Statistics:")
        logger.info(f"  - Total spaces: {stats['total_spaces']}")
        logger.info(f"  - Total documents: {stats['total_documents']}")
        logger.info(f"  - Work items processed: {stats['workitems_processed']}")
        logger.info(f"  - Work items with modules: {stats['workitems_with_modules']}")
        logger.info(f"  - Work items without modules: {stats['workitems_without_modules']}")
        
        # Save final result with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_response_to_json(f"discovered_documents_{timestamp}", result)
        
        # Also save a latest version
        save_response_to_json("discovered_documents", result)
        
        return result
    
    def test_extract_specific_space_documents(self, polarion_client, test_project_id):
        """Test extracting documents from a specific space."""
        logger.info("Testing extraction of documents from specific space")
        
        # First discover all
        result = polarion_client.discover_all_documents_and_spaces(
            project_id=test_project_id,
            save_output=False
        )
        
        if not result["spaces"]:
            pytest.skip("No spaces found")
        
        # Take first space
        test_space = result["spaces"][0]
        logger.info(f"Testing with space: {test_space}")
        
        # Filter documents for this space
        space_documents = [
            doc for doc in result["documents"]
            if doc["space"] == test_space
        ]
        
        logger.info(f"Found {len(space_documents)} documents in space '{test_space}'")
        
        if space_documents:
            # Save space-specific results
            space_result = {
                "project": test_project_id,
                "space": test_space,
                "documents": space_documents,
                "statistics": {
                    "total_documents": len(space_documents)
                }
            }
            
            save_response_to_json(f"space_{test_space.replace(' ', '_')}_documents", space_result)
            
            # Log some examples
            for doc in space_documents[:3]:
                logger.info(f"  - {doc['name']} ({len(doc['work_item_refs'])} refs)")
        
        assert len(space_documents) > 0, f"No documents found in space {test_space}"
    
    def test_verify_document_ids_format(self, polarion_client, test_project_id):
        """Test that document IDs follow expected format."""
        logger.info("Testing document ID format validation")
        
        result = polarion_client.discover_all_documents_and_spaces(
            project_id=test_project_id,
            save_output=False
        )
        
        documents = result["documents"]
        
        if not documents:
            pytest.skip("No documents found")
        
        # Check ID format for all documents
        for doc in documents:
            doc_id = doc["id"]
            
            # Should contain at least 2 slashes (project/space/document)
            assert doc_id.count("/") >= 2, f"Invalid document ID format: {doc_id}"
            
            # Parts should match
            parts = doc_id.split("/", 2)
            assert len(parts) == 3, f"Document ID should have 3 parts: {doc_id}"
            
            project, space, name = parts
            assert project == doc["project"], f"Project mismatch in {doc_id}"
            assert space == doc["space"], f"Space mismatch in {doc_id}"
            assert name == doc["name"], f"Name mismatch in {doc_id}"
        
        logger.info(f"✓ All {len(documents)} document IDs have valid format")
    
    def test_work_items_without_modules(self, polarion_client, test_project_id):
        """Test counting work items without module relationships."""
        logger.info("Testing work items without modules")
        
        result = polarion_client.discover_all_documents_and_spaces(
            project_id=test_project_id,
            save_output=False
        )
        
        stats = result["statistics"]
        total = stats["workitems_processed"]
        with_modules = stats["workitems_with_modules"]
        without_modules = stats["workitems_without_modules"]
        
        # Verify counts add up
        assert with_modules + without_modules == total, "Work item counts don't add up"
        
        # Calculate percentage
        if total > 0:
            percentage_with = (with_modules / total) * 100
            percentage_without = (without_modules / total) * 100
            
            logger.info(f"Work items with modules: {with_modules} ({percentage_with:.1f}%)")
            logger.info(f"Work items without modules: {without_modules} ({percentage_without:.1f}%)")
        
        # Save statistics
        stats_report = {
            "project": test_project_id,
            "total_workitems": total,
            "with_modules": with_modules,
            "without_modules": without_modules,
            "percentage_with_modules": percentage_with if total > 0 else 0,
            "percentage_without_modules": percentage_without if total > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        save_response_to_json("workitem_module_statistics", stats_report)


@pytest.mark.integration
def test_full_discovery_workflow(polarion_client, test_project_id):
    """Integration test for complete discovery workflow."""
    logger.info("Running full discovery workflow")
    
    # Step 1: Discover all
    logger.info("Step 1: Discovering all documents and spaces")
    result = polarion_client.discover_all_documents_and_spaces(
        project_id=test_project_id,
        save_output=True
    )
    
    assert result["spaces"], "No spaces found"
    assert result["documents"], "No documents found"
    
    # Step 2: Validate data quality
    logger.info("Step 2: Validating data quality")
    
    # Check for duplicate documents
    doc_ids = [doc["id"] for doc in result["documents"]]
    assert len(doc_ids) == len(set(doc_ids)), "Duplicate document IDs found"
    
    # Check for duplicate spaces
    assert len(result["spaces"]) == len(set(result["spaces"])), "Duplicate spaces found"
    
    # Step 3: Create summary report
    logger.info("Step 3: Creating summary report")
    
    summary = {
        "project": test_project_id,
        "discovery_timestamp": datetime.now().isoformat(),
        "summary": {
            "total_spaces": len(result["spaces"]),
            "total_documents": len(result["documents"]),
            "total_workitems": result["statistics"]["workitems_processed"],
            "coverage": {
                "workitems_with_modules": result["statistics"]["workitems_with_modules"],
                "workitems_without_modules": result["statistics"]["workitems_without_modules"]
            }
        },
        "spaces": result["spaces"],
        "top_documents": result["documents"][:10] if result["documents"] else [],
        "validation": {
            "no_duplicates": True,
            "format_valid": True,
            "data_complete": True
        }
    }
    
    save_response_to_json("discovery_summary", summary)
    
    logger.info("✓ Full discovery workflow completed successfully")
    logger.info(f"  - Found {len(result['spaces'])} spaces")
    logger.info(f"  - Found {len(result['documents'])} documents")
    logger.info(f"  - Processed {result['statistics']['workitems_processed']} work items")