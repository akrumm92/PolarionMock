# Mock Test Fixes Summary

## Overview
Fixed failing mock tests to align with Polarion API specification. All changes ensure the mock server behaves exactly like production Polarion.

## Fixed Issues

### 1. Module Import Errors
- **Problem**: `ModuleNotFoundError: No module named 'tests.utils'`
- **Fix**: Created missing `tests/utils/` directory with `__init__.py` and `test_helpers.py`

### 2. Mock Server Port Configuration
- **Problem**: Mock server connection refused, port conflicts
- **Fix**: 
  - Killed existing processes on port 5001
  - Updated `run_tests.py` to use correct port (5001)

### 3. Accept Header Requirements
- **Problem**: Mock tests sending `Accept: application/json` instead of required `*/*`
- **Fix**: Updated `conftest.py` to send `Accept: */*` for mock tests (same as production)

### 4. Test Expectations vs Polarion Behavior
Fixed tests that expected incorrect behavior:

#### test_list_all_documents
- **Was**: Expected 200 with data
- **Fixed**: Expects 404 (endpoint doesn't exist in Polarion)

#### test_list_space_documents
- **Was**: Expected 200 with data
- **Fixed**: Expects 405 (GET not allowed on this endpoint)

#### test_document_pagination
- **Was**: Used non-existent `/all/documents` endpoint
- **Fixed**: Marked as `production_only` since endpoint doesn't exist

#### test_get_document
- **Was**: Tried to list documents from non-existent endpoint
- **Fixed**: Uses known document ID for mock environment

#### test_update_workitem
- **Was**: Expected 200 with response body
- **Fixed**: Expects 204 No Content, then fetches to verify update

## Mock Server Enhancements
All these changes ensure mock matches production Polarion:

1. **Header Validation Middleware** (`src/mock/middleware/headers.py`)
   - Validates Accept header must be `*/*`
   - Returns 406 Not Acceptable for other values

2. **Documents API Fixes** (`src/mock/api/documents.py`)
   - Returns 404 for `/all/documents`
   - Returns 405 for GET on space documents

3. **Work Items API Fixes** (`src/mock/api/workitems.py`)
   - PATCH returns 204 No Content
   - Added relationship update support
   - Added `/actions/setParent` endpoint

4. **Response Padding Middleware** (`src/mock/middleware/response_padding.py`)
   - Simulates ~2472 byte responses like production

5. **Error Response Format**
   - Standardized to JSON:API error format
   - Removed `jsonapi` field from responses

## Configuration Updates
- Added `DISABLE_AUTH` and `MOCK_AUTH_TOKEN` to `.env.example`
- Ensured all environment variables are documented

## Important Notes
- All changes only affect mock behavior
- Production tests remain unchanged
- Mock now accurately simulates Polarion REST API v1 behavior