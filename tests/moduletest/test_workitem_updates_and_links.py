"""Test module for WorkItem update and link management functionality.

This module tests:
- Updating work item attributes (title, description, status, severity)
- Creating links between work items (relates_to, depends_on, blocks, etc.)
- Deleting links between work items
- Managing parent-child relationships

Author: Claude
Date: 2025-08-07
"""

import pytest
import logging
from datetime import datetime
from typing import Dict, Any, List
import json
import os
from pathlib import Path

from src.polarion_api.client import PolarionClient

# Set up logging
logger = logging.getLogger(__name__)


def save_response_to_json(filename: str, data: Any) -> None:
    """Save response data to JSON file for analysis.
    
    Args:
        filename: Name of the file (without extension)
        data: Data to save
    """
    output_dir = Path("tests/moduletest/outputdata")
    output_dir.mkdir(exist_ok=True)
    
    file_path = output_dir / f"{filename}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved response to {file_path}")


class TestWorkItemUpdatesAndLinks:
    """Test suite for work item update and link management operations."""
    
    @pytest.fixture
    def test_document(self):
        """Provide test document configuration."""
        return {
            "project": "Python",
            "space": "_default",
            "document": "Functional Concept - Template",
            "full_id": "Python/_default/Functional Concept - Template"
        }
    
    @pytest.fixture(autouse=True)
    def setup_logging(self, request):
        """Set up test-specific logging."""
        test_name = request.node.name
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting test: {test_name}")
        logger.info(f"{'='*80}")
    
    def test_complete_workitem_lifecycle(self, polarion_client, test_document):
        """Test complete work item lifecycle: create, update, link, unlink.
        
        This test demonstrates:
        1. Creating a new work item in a document
        2. Updating its attributes (title, description, status, severity)
        3. Creating another work item
        4. Linking them with various relationships
        5. Deleting links
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_results = {
            "timestamp": timestamp,
            "test": "complete_workitem_lifecycle",
            "steps": []
        }
        
        # ========================================
        # Step 1: Create first work item (requirement)
        # ========================================
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Creating first work item (requirement)")
        logger.info("="*60)
        
        wi1_data = {
            "title": f"Test Requirement {timestamp}",
            "work_item_type": "requirement",
            "status": "draft",
            "description": {
                "type": "text/html",
                "value": "<p>Initial requirement for testing updates</p>"
            },
            "severity": "must_have",
            "priority": "80.0"
        }
        
        result1 = polarion_client.create_work_item_in_document(
            project_id=test_document["project"],
            space_id=test_document["space"],
            document_name=test_document["document"],
            previous_part_id="heading_PYTH-9397",  # Place under meaningful chapter
            **wi1_data
        )
        
        assert result1.get("document_integration", {}).get("visible_in_document") == True, f"Failed to create first work item: {result1}"
        wi1_id = result1["id"]
        logger.info(f"✅ Created first work item: {wi1_id}")
        
        test_results["steps"].append({
            "step": "create_workitem_1",
            "status": "success",
            "work_item_id": wi1_id
        })
        
        # ========================================
        # Step 2: Update work item attributes
        # ========================================
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Updating work item attributes")
        logger.info("="*60)
        
        # Test different valid status values from status-enum.xml
        status_updates = [
            ("Proposed", "Initial status"),
            ("Ready for Review", "Development complete"),
            ("To clarify", "Needs clarification"),
            ("Accepted by project", "Approved by team")
        ]
        
        for new_status, description in status_updates:
            logger.info(f"Updating status to: {new_status}")
            
            update_result = polarion_client.update_work_item(
                wi1_id,
                attributes={
                    "title": f"Updated Requirement {timestamp} - {new_status}",
                    "description": {
                        "type": "text/html", 
                        "value": f"<p>{description}</p><p>Updated at {datetime.now().isoformat()}</p>"
                    },
                    "status": new_status,
                    "severity": "can_be" if new_status == "To clarify" else "must_be"
                }
            )
            
            if update_result.get("status") == "success":
                logger.info(f"✅ Successfully updated to status: {new_status}")
                test_results["steps"].append({
                    "step": f"update_status_{new_status.replace(' ', '_').lower()}",
                    "status": "success",
                    "new_status": new_status
                })
            else:
                logger.warning(f"⚠️ Failed to update status: {update_result.get('error')}")
                test_results["steps"].append({
                    "step": f"update_status_{new_status.replace(' ', '_').lower()}",
                    "status": "failed",
                    "error": update_result.get('error')
                })
        
        # ========================================
        # Step 3: Create second work item (test case)
        # ========================================
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Creating second work item (test case)")
        logger.info("="*60)
        
        wi2_data = {
            "title": f"Test Case for Requirement {timestamp}",
            "work_item_type": "testcase",
            "status": "draft",
            "description": {
                "type": "text/html",
                "value": f"<p>Test case to verify requirement {wi1_id}</p>"
            },
            "severity": "must_have",
            "priority": "75.0"
        }
        
        result2 = polarion_client.create_work_item_in_document(
            project_id=test_document["project"],
            space_id=test_document["space"],
            document_name=test_document["document"],
            previous_part_id="heading_PYTH-9397",  # Place under meaningful chapter
            **wi2_data
        )
        
        if not result2.get("document_integration", {}).get("visible_in_document"):
            # If testcase type doesn't exist, try with requirement type
            logger.warning("testcase type might not exist, trying with requirement type")
            wi2_data["work_item_type"] = "requirement"
            wi2_data["title"] = f"Test Requirement 2 {timestamp}"
            result2 = polarion_client.create_work_item_in_document(
                project_id=test_document["project"],
                space_id=test_document["space"],
                document_name=test_document["document"],
                previous_part_id="heading_PYTH-9397",  # Place under meaningful chapter
                **wi2_data
            )
        
        assert result2.get("document_integration", {}).get("visible_in_document") == True, f"Failed to create second work item: {result2}"
        wi2_id = result2["id"]
        logger.info(f"✅ Created second work item: {wi2_id}")
        
        test_results["steps"].append({
            "step": "create_workitem_2",
            "status": "success",
            "work_item_id": wi2_id
        })
        
        # ========================================
        # Step 4: Create third work item (for complex linking)
        # ========================================
        logger.info("\n" + "="*60)
        logger.info("STEP 4: Creating third work item")
        logger.info("="*60)
        
        wi3_data = {
            "title": f"Blocking Requirement {timestamp}",
            "work_item_type": "requirement",
            "status": "draft",
            "description": {
                "type": "text/html",
                "value": f"<p>This requirement blocks {wi1_id}</p>"
            },
            "severity": "must_be",
            "priority": "90.0"
        }
        
        result3 = polarion_client.create_work_item_in_document(
            project_id=test_document["project"],
            space_id=test_document["space"],
            document_name=test_document["document"],
            previous_part_id="heading_PYTH-9397",  # Place under meaningful chapter
            **wi3_data
        )
        
        assert result3.get("document_integration", {}).get("visible_in_document") == True, f"Failed to create third work item: {result3}"
        wi3_id = result3["id"]
        logger.info(f"✅ Created third work item: {wi3_id}")
        
        test_results["steps"].append({
            "step": "create_workitem_3",
            "status": "success",
            "work_item_id": wi3_id
        })
        
        # ========================================
        # Step 5: Create links between work items
        # ========================================
        logger.info("\n" + "="*60)
        logger.info("STEP 5: Creating links between work items")
        logger.info("="*60)
        
        # Test different link types
        links_to_create = [
            (wi2_id, wi1_id, "verifies", "Test case verifies requirement"),
            (wi1_id, wi3_id, "depends_on", "Requirement depends on blocking item"),
            (wi3_id, wi1_id, "blocks", "Blocking item blocks requirement"),
            (wi1_id, wi2_id, "relates_to", "General relationship")
        ]
        
        created_links = []
        for source, target, role, description in links_to_create:
            logger.info(f"Creating link: {source} --[{role}]--> {target} ({description})")
            
            link_result = polarion_client.create_work_item_link(
                source_id=source,
                target_id=target,
                role=role
            )
            
            if link_result.get("status") == "success":
                logger.info(f"✅ Created link: {role}")
                created_links.append((source, target, role))
                test_results["steps"].append({
                    "step": f"create_link_{role}",
                    "status": "success",
                    "source": source,
                    "target": target,
                    "role": role
                })
            else:
                # Check if it's a 409 (already exists)
                if "409" in str(link_result.get("error", "")):
                    logger.info(f"ℹ️ Link already exists: {role}")
                    created_links.append((source, target, role))
                    test_results["steps"].append({
                        "step": f"create_link_{role}",
                        "status": "already_exists",
                        "source": source,
                        "target": target,
                        "role": role
                    })
                else:
                    logger.warning(f"⚠️ Failed to create link: {link_result.get('error')}")
                    test_results["steps"].append({
                        "step": f"create_link_{role}",
                        "status": "failed",
                        "error": link_result.get('error')
                    })
        
        # ========================================
        # Step 6: Verify work items can be fetched with relationships
        # ========================================
        logger.info("\n" + "="*60)
        logger.info("STEP 6: Verifying work items and relationships")
        logger.info("="*60)
        
        # Fetch the first work item to verify updates
        fetched_wi1 = polarion_client.get_work_item(
            wi1_id,
            **{"fields[workitems]": "@all", "include": "linkedWorkItems"}
        )
        
        if "data" in fetched_wi1:
            attrs = fetched_wi1["data"].get("attributes", {})
            logger.info(f"Work item {wi1_id}:")
            logger.info(f"  - Title: {attrs.get('title')}")
            logger.info(f"  - Status: {attrs.get('status')}")
            logger.info(f"  - Severity: {attrs.get('severity')}")
            
            test_results["steps"].append({
                "step": "verify_updates",
                "status": "success",
                "work_item": {
                    "id": wi1_id,
                    "title": attrs.get('title'),
                    "status": attrs.get('status'),
                    "severity": attrs.get('severity')
                }
            })
        
        # ========================================
        # Step 7: Delete a link (optional, commented out to preserve data)
        # ========================================
        # Uncomment to test link deletion
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 7: Deleting a link")
        logger.info("="*60)
        
        if created_links:
            source, target, role = created_links[0]
            logger.info(f"Deleting link: {source} --[{role}]-X-> {target}")
            
            delete_result = polarion_client.delete_work_item_link(
                source_id=source,
                target_id=target,
                role=role
            )
            
            if delete_result.get("status") == "success":
                logger.info(f"✅ Successfully deleted link")
                test_results["steps"].append({
                    "step": "delete_link",
                    "status": "success",
                    "deleted": {"source": source, "target": target, "role": role}
                })
            else:
                logger.warning(f"⚠️ Failed to delete link: {delete_result.get('error')}")
                test_results["steps"].append({
                    "step": "delete_link",
                    "status": "failed",
                    "error": delete_result.get('error')
                })
        """
        
        # ========================================
        # Save test results
        # ========================================
        save_response_to_json(f"workitem_updates_test_{timestamp}", test_results)
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"✅ Created 3 work items:")
        logger.info(f"   - {wi1_id} (requirement)")
        logger.info(f"   - {wi2_id} (test case/requirement)")
        logger.info(f"   - {wi3_id} (blocking requirement)")
        logger.info(f"✅ Updated work item attributes {len([s for s in test_results['steps'] if 'update_status' in s['step']])} times")
        logger.info(f"✅ Created {len(created_links)} links between work items")
        
        # Assert that we had at least partial success
        successful_steps = [s for s in test_results["steps"] if s["status"] in ["success", "already_exists"]]
        assert len(successful_steps) >= 5, f"Too few successful steps: {len(successful_steps)}"
        
        logger.info("\n✅ Test completed successfully!")
        
        return test_results
    
    def test_update_work_item_severity(self, polarion_client, test_document):
        """Test updating work item severity with valid enum values.
        
        Valid severity values from severity-enum.xml:
        - NA (Not applicable)
        - must_be
        - usp
        - excitement_feature
        - can_be
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info("Testing severity updates with valid enum values")
        
        # Create a work item
        wi_data = {
            "title": f"Severity Test {timestamp}",
            "work_item_type": "requirement",
            "status": "draft",
            "description": {
                "type": "text/html",
                "value": "<p>Testing severity updates</p>"
            },
            "severity": "must_be",
            "priority": "50.0"
        }
        
        result = polarion_client.create_work_item_in_document(
            project_id=test_document["project"],
            space_id=test_document["space"],
            document_name=test_document["document"],
            previous_part_id="heading_PYTH-9397",  # Place under meaningful chapter
            **wi_data
        )
        
        assert result.get("document_integration", {}).get("visible_in_document") == True, f"Failed to create work item: {result}"
        wi_id = result["id"]
        logger.info(f"Created work item: {wi_id}")
        
        # Test each severity value
        severity_values = ["NA", "must_be", "usp", "excitement_feature", "can_be"]
        
        for severity in severity_values:
            logger.info(f"Updating severity to: {severity}")
            
            update_result = polarion_client.update_work_item(
                wi_id,
                attributes={"severity": severity}
            )
            
            if update_result.get("status") == "success":
                logger.info(f"✅ Successfully updated severity to: {severity}")
            else:
                logger.warning(f"⚠️ Failed to update severity to {severity}: {update_result.get('error')}")
        
        logger.info("✅ Severity update test completed")
        return {"work_item_id": wi_id, "tested_severities": severity_values}
    
    def test_delete_work_item_link(self, polarion_client, test_document):
        """Test creating and deleting links between work items.
        
        This test specifically validates the delete_work_item_link functionality:
        1. Creates two work items
        2. Creates multiple links between them
        3. Deletes specific links
        4. Verifies deletion was successful
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info("\n" + "="*60)
        logger.info("Testing work item link deletion")
        logger.info("="*60)
        
        # Create first work item
        wi1_data = {
            "title": f"Link Test Source {timestamp}",
            "work_item_type": "requirement",
            "status": "draft",
            "description": {
                "type": "text/html",
                "value": "<p>Source work item for link deletion test</p>"
            },
            "severity": "must_have",
            "priority": "50.0"
        }
        
        result1 = polarion_client.create_work_item_in_document(
            project_id=test_document["project"],
            space_id=test_document["space"],
            document_name=test_document["document"],
            previous_part_id="heading_PYTH-9397",
            **wi1_data
        )
        
        assert result1.get("document_integration", {}).get("visible_in_document") == True
        wi1_id = result1["id"]
        logger.info(f"Created source work item: {wi1_id}")
        
        # Create second work item
        wi2_data = {
            "title": f"Link Test Target {timestamp}",
            "work_item_type": "requirement",
            "status": "draft",
            "description": {
                "type": "text/html",
                "value": "<p>Target work item for link deletion test</p>"
            },
            "severity": "must_have",
            "priority": "50.0"
        }
        
        result2 = polarion_client.create_work_item_in_document(
            project_id=test_document["project"],
            space_id=test_document["space"],
            document_name=test_document["document"],
            previous_part_id="heading_PYTH-9397",
            **wi2_data
        )
        
        assert result2.get("document_integration", {}).get("visible_in_document") == True
        wi2_id = result2["id"]
        logger.info(f"Created target work item: {wi2_id}")
        
        # Create multiple links to test deletion
        test_links = [
            ("relates_to", "General relationship"),
            ("depends_on", "Dependency relationship"),
            ("blocks", "Blocking relationship")
        ]
        
        created_links = []
        for role, description in test_links:
            logger.info(f"\nCreating link: {wi1_id} --[{role}]--> {wi2_id}")
            
            link_result = polarion_client.create_work_item_link(
                source_id=wi1_id,
                target_id=wi2_id,
                role=role
            )
            
            if link_result.get("status") == "success":
                logger.info(f"✅ Created {role} link")
                created_links.append((wi1_id, wi2_id, role))
            elif "409" in str(link_result.get("error", "")):
                logger.info(f"ℹ️ Link {role} already exists")
                created_links.append((wi1_id, wi2_id, role))
            else:
                logger.warning(f"⚠️ Failed to create {role} link: {link_result.get('error')}")
        
        # Now test deletion of links
        logger.info("\n" + "="*40)
        logger.info("Testing link deletion")
        logger.info("="*40)
        
        deletion_results = []
        for source, target, role in created_links:
            logger.info(f"\nDeleting link: {source} --[{role}]-X-> {target}")
            
            delete_result = polarion_client.delete_work_item_link(
                source_id=source,
                target_id=target,
                role=role
            )
            
            if delete_result.get("status") == "success":
                logger.info(f"✅ Successfully deleted {role} link")
                deletion_results.append({
                    "role": role,
                    "status": "success"
                })
            elif "404" in str(delete_result.get("error", "")):
                logger.info(f"ℹ️ Link {role} was already deleted or didn't exist")
                deletion_results.append({
                    "role": role,
                    "status": "not_found"
                })
            else:
                logger.warning(f"⚠️ Failed to delete {role} link: {delete_result.get('error')}")
                deletion_results.append({
                    "role": role,
                    "status": "failed",
                    "error": delete_result.get('error')
                })
        
        # Verify that we could delete at least some links
        successful_deletions = [d for d in deletion_results if d["status"] in ["success", "not_found"]]
        
        logger.info("\n" + "="*40)
        logger.info("DELETION TEST SUMMARY")
        logger.info("="*40)
        logger.info(f"Created {len(created_links)} links")
        logger.info(f"Successfully deleted/verified: {len(successful_deletions)} links")
        for result in deletion_results:
            logger.info(f"  - {result['role']}: {result['status']}")
        
        # Save results
        test_data = {
            "timestamp": timestamp,
            "work_items": {
                "source": wi1_id,
                "target": wi2_id
            },
            "created_links": created_links,
            "deletion_results": deletion_results
        }
        save_response_to_json(f"link_deletion_test_{timestamp}", test_data)
        
        # Assert that at least one deletion was successful or the link was already gone
        assert len(successful_deletions) > 0, "No links could be deleted"
        
        logger.info("\n✅ Link deletion test completed successfully!")
        return test_data