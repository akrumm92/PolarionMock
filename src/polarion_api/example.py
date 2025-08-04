#!/usr/bin/env python3
"""
Example usage of the Polarion API client.

This script demonstrates various features of the polarion_api module.
"""

import logging
from datetime import datetime
from polarion_api import PolarionClient, PolarionError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main example function."""
    
    # Initialize client
    logger.info("Initializing Polarion client...")
    
    try:
        with PolarionClient() as client:
            # Test connection
            logger.info("Testing connection...")
            client.test_connection()
            logger.info("✓ Connection successful!")
            
            # List projects
            logger.info("\n=== Projects ===")
            projects = client.get_projects()
            logger.info(f"Found {len(projects['data'])} projects:")
            
            for project in projects['data'][:5]:  # First 5 projects
                attrs = project.get('attributes', {})
                logger.info(f"  - {project['id']}: {attrs.get('name', 'N/A')}")
            
            # Work with a specific project
            project_id = "myproject"  # Change this to your project ID
            
            # Create a work item
            logger.info(f"\n=== Creating Work Item in {project_id} ===")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            try:
                work_item = client.create_work_item(
                    project_id=project_id,
                    title=f"Test Requirement {timestamp}",
                    work_item_type="requirement",
                    description={
                        "type": "text/html",
                        "value": f"<p>This is a test requirement created at {timestamp}</p>"
                    },
                    priority="high",
                    status="proposed",
                    severity="major"
                )
                
                work_item_id = work_item['id']
                logger.info(f"✓ Created work item: {work_item_id}")
                
                # Update the work item
                logger.info(f"\n=== Updating Work Item ===")
                client.update_work_item(
                    work_item_id=work_item_id,
                    status="in_progress",
                    priority="critical"
                )
                logger.info(f"✓ Updated work item status and priority")
                
                # Query work items
                logger.info(f"\n=== Querying Work Items ===")
                results = client.query_work_items(
                    query="type:requirement AND status:in_progress",
                    project_id=project_id,
                    **{"page[size]": 10}
                )
                
                logger.info(f"Found {len(results['data'])} work items matching query:")
                for item in results['data'][:3]:  # First 3 items
                    attrs = item.get('attributes', {})
                    logger.info(f"  - {item['id']}: {attrs.get('title', 'N/A')}")
                
                # Create a document
                logger.info(f"\n=== Creating Document ===")
                try:
                    doc = client.create_document(
                        project_id=project_id,
                        space_id="_default",
                        module_name=f"test_spec_{timestamp}",
                        title=f"Test Specification {timestamp}",
                        document_type="req_specification",
                        home_page_content={
                            "type": "text/html",
                            "value": f"<h1>Test Specification</h1><p>Created at {timestamp}</p>"
                        }
                    )
                    
                    document_id = doc['id']
                    logger.info(f"✓ Created document: {document_id}")
                    
                    # Add work item to document
                    logger.info(f"\n=== Adding Work Item to Document ===")
                    client.add_work_item_to_document(
                        document_id=document_id,
                        work_item_id=work_item_id
                    )
                    logger.info(f"✓ Added work item to document")
                    
                except PolarionError as e:
                    logger.warning(f"Document operations may not be supported: {e}")
                
                # Clean up - delete the work item
                logger.info(f"\n=== Cleanup ===")
                client.delete_work_item(work_item_id)
                logger.info(f"✓ Deleted test work item")
                
            except PolarionError as e:
                logger.error(f"Error during work item operations: {e}")
                if hasattr(e, 'errors') and e.errors:
                    for error in e.errors:
                        logger.error(f"  - {error.get('detail', error)}")
            
            # Demonstrate error handling
            logger.info(f"\n=== Error Handling Example ===")
            try:
                # Try to get non-existent work item
                client.get_work_item("nonexistent/FAKE-999")
            except PolarionError as e:
                logger.info(f"Expected error caught: {e}")
            
            logger.info("\n✓ Example completed successfully!")
            
    except PolarionError as e:
        logger.error(f"Failed to initialize client: {e}")
        logger.error("Please check your .env configuration")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())