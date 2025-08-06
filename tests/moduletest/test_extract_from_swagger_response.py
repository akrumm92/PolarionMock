"""
Test to extract documents and spaces from the existing SwaggerUiResponse.json file.
This demonstrates the extraction logic without needing a live Polarion connection.
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_documents_and_spaces_from_json(json_file: str) -> dict:
    """Extract documents and spaces from saved JSON response.
    
    Args:
        json_file: Path to the JSON file with work items response
        
    Returns:
        Dictionary with extracted documents and spaces
    """
    logger.info(f"Loading data from {json_file}")
    
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Get work items
    work_items = data.get("data", [])
    logger.info(f"Found {len(work_items)} work items in file")
    
    # Extract documents and spaces
    spaces = set()
    documents_map = {}
    workitems_with_modules = 0
    workitems_without_modules = 0
    
    for wi in work_items:
        wi_id = wi.get("id", "unknown")
        relationships = wi.get("relationships", {})
        module = relationships.get("module", {})
        module_data = module.get("data")
        
        if module_data and isinstance(module_data, dict):
            doc_id = module_data.get("id")
            if doc_id:
                workitems_with_modules += 1
                
                # Parse document ID (format: project/space/document)
                if "/" in doc_id:
                    parts = doc_id.split("/", 2)  # Split max 2 times
                    if len(parts) >= 3:
                        project = parts[0]
                        space = parts[1]
                        doc_name = parts[2]
                        
                        # Add space
                        spaces.add(space)
                        
                        # Add document (deduplicated by ID)
                        if doc_id not in documents_map:
                            documents_map[doc_id] = {
                                "id": doc_id,
                                "project": project,
                                "space": space,
                                "name": doc_name,
                                "work_item_refs": [wi_id]
                            }
                        else:
                            # Add work item reference
                            documents_map[doc_id]["work_item_refs"].append(wi_id)
                        
                        logger.debug(f"Work item {wi_id} -> Document: {doc_id}")
        else:
            workitems_without_modules += 1
    
    # Convert to lists and sort
    spaces_list = sorted(list(spaces))
    documents = sorted(list(documents_map.values()), key=lambda d: d["id"])
    
    # Create result
    result = {
        "project": "Python",  # From the file
        "spaces": spaces_list,
        "documents": documents,
        "statistics": {
            "total_spaces": len(spaces_list),
            "total_documents": len(documents),
            "workitems_processed": len(work_items),
            "workitems_with_modules": workitems_with_modules,
            "workitems_without_modules": workitems_without_modules
        }
    }
    
    return result


def save_result(result: dict, output_dir: str = "tests/moduletest/outputdata"):
    """Save extraction result to JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"extracted_documents_{timestamp}.json")
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # Also save as latest
    latest_path = os.path.join(output_dir, "extracted_documents_from_swagger.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved results to {filepath}")
    logger.info(f"Also saved as {latest_path}")
    
    return filepath


def main():
    """Main function to run extraction."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    
    # Path to the SwaggerUiResponse.json file
    json_file = "test_reports/20250806_101810/SwaggerUiResponse.json"
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        return
    
    # Extract documents and spaces
    result = extract_documents_and_spaces_from_json(json_file)
    
    # Log summary
    logger.info("=" * 60)
    logger.info("EXTRACTION RESULTS:")
    logger.info("=" * 60)
    logger.info(f"Project: {result['project']}")
    logger.info(f"Spaces found: {result['statistics']['total_spaces']}")
    if result['spaces']:
        logger.info(f"Space names: {', '.join(result['spaces'])}")
    
    logger.info(f"Documents found: {result['statistics']['total_documents']}")
    if result['documents']:
        logger.info("Sample documents:")
        for doc in result['documents'][:5]:
            logger.info(f"  - {doc['id']} ({len(doc['work_item_refs'])} work items)")
    
    logger.info(f"Work items processed: {result['statistics']['workitems_processed']}")
    logger.info(f"  - With modules: {result['statistics']['workitems_with_modules']}")
    logger.info(f"  - Without modules: {result['statistics']['workitems_without_modules']}")
    
    # Save results
    save_result(result)
    
    # Print final summary
    logger.info("=" * 60)
    logger.info("✓ Extraction completed successfully!")
    logger.info(f"✓ Found {len(result['spaces'])} unique spaces")
    logger.info(f"✓ Found {len(result['documents'])} unique documents")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()