# Fix Documentation: Polarion Space Discovery

## Problem Summary

The space discovery implementation introduced in commits 9e9b369 and a3a759d was using **non-existent Polarion API endpoints**, causing 404 errors when running tests against production Polarion.

## Root Cause

The implementation incorrectly assumed these endpoints exist in Polarion REST API v1:
- ❌ `/projects/{projectId}/documents` - **DOES NOT EXIST**
- ❌ `/projects/{projectId}/spaces/{spaceId}/documents` - **DOES NOT EXIST**

### What Actually Exists in Polarion

Polarion REST API v1 only provides:
- ✅ `/projects/{projectId}/spaces/{spaceId}/documents/{documentId}` - Get a **single** document
- NO bulk endpoints for listing documents
- NO endpoint for listing spaces

## The Solution

Since Polarion doesn't provide bulk endpoints, the fixed implementation:

1. **Tests known space/document combinations** to discover what exists
2. **Uses only the single-document endpoint** that actually exists
3. **Handles 404 errors gracefully** when a space/document doesn't exist

### Key Changes in `src/polarion_api/documents.py`

#### 1. `get_all_project_documents_and_spaces()`
**Before:** Tried to use `/projects/{projectId}/documents` (doesn't exist)
**After:** Discovers spaces first, then tests specific documents in each space

#### 2. `list_documents_in_space()`
**Before:** Tried to use `/projects/{projectId}/spaces/{spaceId}/documents` (doesn't exist)
**After:** Tests a list of common document names using the single-document endpoint

#### 3. `_fallback_space_discovery()`
**Before:** Tried bulk document listing
**After:** Tests specific document names to verify space existence

## Implementation Details

### Space Discovery Strategy

```python
# Common spaces to test
potential_spaces = [
    "_default", "Default", "Requirements", "TestCases", 
    "Documents", "Specifications", "Design", "Tests", ...
]

# Common documents to look for
test_documents = [
    "_project", "index", "readme", "overview", 
    "requirements", "specifications", ...
]

# For each space/document combination:
# Try: GET /projects/{project}/spaces/{space}/documents/{document}
# If 200 OK: Space exists!
```

### Limitations

Due to Polarion's API limitations:
- Cannot get a complete list of all documents
- Cannot paginate through documents
- Can only discover spaces/documents we specifically test for
- Discovery is slower (multiple API calls needed)

## Testing the Fix

### 1. Run Diagnostic Script
```bash
python scripts/diagnose_connection.py
```

### 2. Test the Fixed Implementation
```bash
python test_space_discovery_fixed.py
```

### 3. Run Full Test Suite
```bash
python run_tests.py --env production
```

## Files Modified

1. **`src/polarion_api/documents.py`** - Core fix
   - `get_all_project_documents_and_spaces()` - Corrected
   - `list_documents_in_space()` - Corrected
   - `_fallback_space_discovery()` - Corrected

2. **Created for debugging:**
   - `scripts/diagnose_connection.py` - Connection diagnostics
   - `test_space_discovery_fixed.py` - Test corrected implementation
   - `docs/TROUBLESHOOTING_CONNECTION.md` - Troubleshooting guide
   - `RUN_ON_WINDOWS.bat` - Windows test runner with diagnostics

## Commit Message Suggestion

```
Fix: Correct space discovery to use existing Polarion endpoints

Problem:
- Space discovery was using non-existent bulk endpoints
- /projects/{id}/documents doesn't exist in Polarion
- /projects/{id}/spaces/{space}/documents doesn't exist either

Solution:
- Only use the single-document endpoint that actually exists
- Test known document names in potential spaces
- Handle 404 errors gracefully

This fixes the 404 errors when running tests against production Polarion.
The implementation now works within Polarion's API limitations.
```

## Lessons Learned

1. **Always verify API endpoints exist** before implementing
2. **Polarion REST API v1 is limited** - no bulk operations for documents
3. **Test against production early** to catch API mismatches
4. **Document API limitations clearly** in code comments

## Next Steps

1. Run `python test_space_discovery_fixed.py` on Windows test machine
2. Verify all discovery tests pass
3. Consider caching discovered spaces to reduce API calls
4. Update mock server to match these API limitations