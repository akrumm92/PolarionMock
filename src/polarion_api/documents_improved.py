"""
Improved get_project_spaces implementation that works with Polarion's actual API limitations.
"""

def get_project_spaces(self, project_id: str) -> List[str]:
    """Get list of available spaces in a project.
    
    Since there's no direct API to list spaces and bulk work item queries don't work,
    this method uses multiple creative strategies:
    1. Try to access specific documents/pages in potential spaces
    2. Use Collections API to find referenced documents
    3. Check test runs for document references
    4. Try known work item ID patterns
    
    Args:
        project_id: The project ID
        
    Returns:
        List of found space IDs
    """
    found_spaces = set()
    logger.info(f"Starting space discovery for project: {project_id}")
    
    # Strategy 1: Test known space names by trying to access resources
    potential_spaces = [
        "_default", "Default", "default",
        "Requirements", "TestCases", "Documents", 
        "Specifications", "Tests", "Design", 
        "Implementation", "Maintenance",
        # Product Layer variations
        "Product Layer", "ProductLayer", "product_layer",
        "Product-Layer", "product-layer", "Product_Layer",
        # Additional common spaces
        "System", "Component", "Architecture",
        "Integration", "Validation", "Verification"
    ]
    
    for space in potential_spaces:
        # Try to get a document in this space
        # We'll try common document names
        for doc_name in ["index", "readme", "overview", "main", "requirements"]:
            try:
                endpoint = f"/projects/{project_id}/spaces/{space}/documents/{doc_name}"
                response = self._request("GET", endpoint)
                if response.status_code == 200:
                    found_spaces.add(space)
                    logger.info(f"Found space '{space}' via document '{doc_name}'")
                    break
                elif response.status_code == 403:  # Forbidden means it exists but no access
                    found_spaces.add(space)
                    logger.info(f"Found space '{space}' (access denied but exists)")
                    break
            except Exception:
                pass
        
        # Try pages endpoint
        if space not in found_spaces:
            try:
                endpoint = f"/projects/{project_id}/spaces/{space}/pages/Home"
                response = self._request("GET", endpoint)
                if response.status_code in [200, 403]:
                    found_spaces.add(space)
                    logger.info(f"Found space '{space}' via pages")
            except Exception:
                pass
    
    # Strategy 2: Use Collections to find document spaces
    try:
        endpoint = f"/projects/{project_id}/collections"
        params = {
            "page[size]": 100,
            "include": "documents"
        }
        response = self._request("GET", endpoint, params=params)
        if response.status_code == 200:
            data = response.json()
            
            # Parse included documents
            for item in data.get("included", []):
                if item.get("type") == "documents":
                    doc_id = item.get("id", "")
                    parts = doc_id.split("/")
                    if len(parts) >= 2 and parts[0] == project_id:
                        space = parts[1]
                        if space and space not in found_spaces:
                            found_spaces.add(space)
                            logger.info(f"Found space '{space}' from collections")
    except Exception as e:
        logger.debug(f"Collections discovery failed: {e}")
    
    # Strategy 3: Check test runs for document references
    try:
        endpoint = f"/projects/{project_id}/testruns"
        params = {"page[size]": 20}
        response = self._request("GET", endpoint, params=params)
        if response.status_code == 200:
            data = response.json()
            for testrun in data.get("data", []):
                # Look for document references in test runs
                testrun_id = testrun.get("id", "")
                if "/" in testrun_id:
                    parts = testrun_id.split("/")
                    if len(parts) > 1:
                        potential_space = parts[1]
                        if potential_space and potential_space not in found_spaces:
                            # Verify this is actually a space
                            try:
                                test_endpoint = f"/projects/{project_id}/spaces/{potential_space}/documents/test"
                                test_response = self._request("HEAD", test_endpoint)
                                if test_response.status_code in [200, 403, 405]:
                                    found_spaces.add(potential_space)
                                    logger.info(f"Found space '{potential_space}' from test runs")
                            except Exception:
                                pass
    except Exception as e:
        logger.debug(f"Test runs discovery failed: {e}")
    
    # Strategy 4: Try specific work item IDs
    # Work item format: projectId/spaceId/type/id
    work_item_types = ["REQ", "TEST", "TASK", "DOC", "ISSUE"]
    
    for space in list(found_spaces)[:3] if found_spaces else potential_spaces[:5]:
        for wi_type in work_item_types:
            for wi_num in ["1", "001", "0001"]:
                try:
                    work_item_id = f"{project_id}/{space}/{wi_type}-{wi_num}"
                    endpoint = f"/projects/{project_id}/workitems/{work_item_id}"
                    response = self._request("GET", endpoint)
                    if response.status_code in [200, 403]:
                        found_spaces.add(space)
                        logger.info(f"Confirmed space '{space}' via work item")
                        break
                except Exception:
                    pass
    
    # Strategy 5: Try Plans endpoint which might reference spaces
    try:
        endpoint = f"/projects/{project_id}/plans"
        params = {"page[size]": 20}
        response = self._request("GET", endpoint, params=params)
        if response.status_code == 200:
            data = response.json()
            for plan in data.get("data", []):
                plan_id = plan.get("id", "")
                # Plans might reference documents/spaces
                attrs = plan.get("attributes", {})
                for key, value in attrs.items():
                    if isinstance(value, str) and "/" in value and project_id in value:
                        parts = value.split("/")
                        for i, part in enumerate(parts):
                            if part == project_id and i + 1 < len(parts):
                                potential_space = parts[i + 1]
                                if potential_space and len(potential_space) < 50:  # Sanity check
                                    # Quick validation
                                    if potential_space not in found_spaces:
                                        try:
                                            test_endpoint = f"/projects/{project_id}/spaces/{potential_space}/documents/test"
                                            test_response = self._request("HEAD", test_endpoint)
                                            if test_response.status_code in [200, 403, 404, 405]:
                                                # 404 might mean no documents but space exists
                                                found_spaces.add(potential_space)
                                                logger.info(f"Found space '{potential_space}' from plans")
                                        except Exception:
                                            pass
    except Exception as e:
        logger.debug(f"Plans discovery failed: {e}")
    
    # Convert to sorted list
    result = sorted(list(found_spaces))
    
    # Log results
    if result:
        logger.info(f"Space discovery completed. Found {len(result)} spaces: {result}")
    else:
        logger.warning(f"No spaces found for project {project_id}")
        # Return empty list - don't assume _default exists
        result = []
    
    return result