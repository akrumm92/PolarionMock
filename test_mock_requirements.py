#!/usr/bin/env python3
"""
Test script to validate Mock Server against MOCK_IMPLEMENTATION_REQUIREMENTS.md

Run with: python test_mock_requirements.py
"""

import os
import sys
import time
import json
import requests
from typing import Dict, Any, List, Optional

# Configuration
MOCK_HOST = os.getenv('MOCK_HOST', 'localhost')
MOCK_PORT = int(os.getenv('MOCK_PORT', 5001))
BASE_URL = f"http://{MOCK_HOST}:{MOCK_PORT}/polarion/rest/v1"

# Use disable auth for testing
os.environ['DISABLE_AUTH'] = 'true'

# Headers as per requirements
HEADERS = {
    'Accept': '*/*',  # CRITICAL: Must be wildcard
    'Content-Type': 'application/json',
    'Authorization': 'Bearer test-token'
}


def print_test(name: str, passed: bool, message: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if message and not passed:
        print(f"  → {message}")


def test_headers_validation():
    """Test that Accept header must be '*/*'."""
    print("\n=== Testing Header Validation ===")
    
    # Test with wrong Accept header (should return 406)
    wrong_headers = {**HEADERS, 'Accept': 'application/json'}
    response = requests.get(f"{BASE_URL}/projects", headers=wrong_headers)
    
    passed = response.status_code == 406
    print_test(
        "Accept header validation",
        passed,
        f"Expected 406, got {response.status_code}"
    )
    
    if passed:
        data = response.json()
        error_msg = data.get('errors', [{}])[0].get('detail', '')
        print(f"  → Error message: {error_msg}")
    
    return passed


def test_nonexistent_endpoints():
    """Test that document/space endpoints return 404."""
    print("\n=== Testing Non-Existent Endpoints ===")
    
    endpoints = [
        '/projects/Python/documents',
        '/projects/Python/spaces',
        '/all/documents'
    ]
    
    all_passed = True
    for endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS)
        passed = response.status_code == 404
        print_test(
            f"GET {endpoint} returns 404",
            passed,
            f"Expected 404, got {response.status_code}"
        )
        all_passed = all_passed and passed
        
        if passed:
            data = response.json()
            error = data.get('errors', [{}])[0]
            print(f"  → Status: {error.get('status')}, Title: {error.get('title')}")
    
    return all_passed


def test_workitems_pagination():
    """Test work items endpoint with pagination."""
    print("\n=== Testing Work Items Pagination ===")
    
    # Test Python project work items
    params = {
        'page[size]': 10,
        'page[number]': 1,
        'fields[workitems]': '@all',
        'include': 'module'
    }
    
    response = requests.get(
        f"{BASE_URL}/projects/Python/workitems",
        headers=HEADERS,
        params=params
    )
    
    passed = response.status_code == 200
    print_test(
        "GET /projects/Python/workitems",
        passed,
        f"Expected 200, got {response.status_code}"
    )
    
    if not passed:
        print(f"  → Response: {response.text[:200]}")
        return False
    
    data = response.json()
    
    # Check response structure
    checks = [
        ('Has links', 'links' in data),
        ('Has data', 'data' in data),
        ('Has self link', data.get('links', {}).get('self') is not None),
        ('Has first link', data.get('links', {}).get('first') is not None),
        ('Has last link', data.get('links', {}).get('last') is not None),
        ('Has portal link', data.get('links', {}).get('portal') is not None),
    ]
    
    all_passed = True
    for check_name, check_passed in checks:
        print_test(f"  {check_name}", check_passed)
        all_passed = all_passed and check_passed
    
    # Check work items have module relationships
    workitems = data.get('data', [])
    if workitems:
        modules_count = sum(
            1 for item in workitems
            if item.get('relationships', {}).get('module')
        )
        module_check = modules_count == len(workitems)
        print_test(
            f"  All work items have module ({modules_count}/{len(workitems)})",
            module_check
        )
        all_passed = all_passed and module_check
        
        # Check module ID format
        if workitems and workitems[0].get('relationships', {}).get('module'):
            module_id = workitems[0]['relationships']['module']['data']['id']
            parts = module_id.split('/')
            format_check = len(parts) == 3
            print_test(
                f"  Module ID format (project/space/document)",
                format_check,
                f"Got: {module_id}"
            )
            all_passed = all_passed and format_check
    
    return all_passed


def test_workitem_attributes():
    """Test work item attributes match requirements."""
    print("\n=== Testing Work Item Attributes ===")
    
    response = requests.get(
        f"{BASE_URL}/projects/Python/workitems",
        headers=HEADERS,
        params={'page[size]': 5}
    )
    
    if response.status_code != 200:
        print_test("Failed to fetch work items", False)
        return False
    
    data = response.json()
    workitems = data.get('data', [])
    
    if not workitems:
        print_test("No work items found", False)
        return False
    
    # Check first work item
    item = workitems[0]
    attrs = item.get('attributes', {})
    
    # Required attributes
    required_attrs = ['id', 'title', 'type', 'status', 'priority', 'created', 'updated']
    all_passed = True
    
    for attr in required_attrs:
        has_attr = attr in attrs
        print_test(f"  Has attribute: {attr}", has_attr)
        all_passed = all_passed and has_attr
    
    # Check priority format (should be decimal string)
    priority = attrs.get('priority', '')
    priority_check = '.' in str(priority) or priority.replace('.', '').isdigit()
    print_test(
        f"  Priority format is decimal string",
        priority_check,
        f"Got: {priority}"
    )
    all_passed = all_passed and priority_check
    
    # Check description format (should be object)
    if 'description' in attrs:
        desc = attrs['description']
        desc_check = isinstance(desc, dict) and 'type' in desc and 'value' in desc
        print_test(
            "  Description is object with type/value",
            desc_check,
            f"Got: {type(desc)}"
        )
        all_passed = all_passed and desc_check
    
    return all_passed


def test_pagination_limits():
    """Test pagination limits (max 100, 1-based)."""
    print("\n=== Testing Pagination Limits ===")
    
    # Test max page size
    response = requests.get(
        f"{BASE_URL}/projects/Python/workitems",
        headers=HEADERS,
        params={'page[size]': 200}  # Request more than 100
    )
    
    if response.status_code != 200:
        print_test("Failed to fetch with large page size", False)
        return False
    
    data = response.json()
    actual_size = len(data.get('data', []))
    size_check = actual_size <= 100
    print_test(
        f"Page size capped at 100",
        size_check,
        f"Got {actual_size} items"
    )
    
    # Test page numbering (should be 1-based)
    response = requests.get(
        f"{BASE_URL}/projects/Python/workitems",
        headers=HEADERS,
        params={'page[number]': 0}  # Try page 0
    )
    
    # Should still work but treat as page 1
    page_check = response.status_code == 200
    print_test(
        "Page 0 treated as page 1",
        page_check,
        f"Got status {response.status_code}"
    )
    
    return size_check and page_check


def test_project_structure():
    """Test that Python project exists with correct structure."""
    print("\n=== Testing Project Structure ===")
    
    # Get Python project
    response = requests.get(f"{BASE_URL}/projects/Python", headers=HEADERS)
    
    project_exists = response.status_code == 200
    print_test(
        "Python project exists",
        project_exists,
        f"Got status {response.status_code}"
    )
    
    if not project_exists:
        return False
    
    data = response.json()
    project = data.get('data', {})
    attrs = project.get('attributes', {})
    
    # Check tracker prefix
    prefix = attrs.get('trackerPrefix', '')
    prefix_check = prefix == 'FCTS'
    print_test(
        f"  Tracker prefix is FCTS",
        prefix_check,
        f"Got: {prefix}"
    )
    
    return project_exists and prefix_check


def main():
    """Run all tests."""
    print("=" * 60)
    print("Mock Server Requirements Validation")
    print(f"Testing against: {BASE_URL}")
    print("=" * 60)
    
    # Wait for server to be ready
    print("\nChecking server availability...")
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get(f"http://{MOCK_HOST}:{MOCK_PORT}/health")
            if response.status_code == 200:
                print("✅ Server is ready")
                break
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                print(f"  Waiting for server... ({i+1}/{max_retries})")
                time.sleep(2)
            else:
                print("❌ Server is not running!")
                print(f"   Please start the mock server: MOCK_PORT={MOCK_PORT} python -m src.mock")
                sys.exit(1)
    
    # Run tests
    results = []
    
    results.append(("Header Validation", test_headers_validation()))
    results.append(("Non-Existent Endpoints", test_nonexistent_endpoints()))
    results.append(("Project Structure", test_project_structure()))
    results.append(("Work Items Pagination", test_workitems_pagination()))
    results.append(("Work Item Attributes", test_workitem_attributes()))
    results.append(("Pagination Limits", test_pagination_limits()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Mock server meets requirements.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()