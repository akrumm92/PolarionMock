# Polarion WorkItem-Document Integration Specification

## Executive Summary

Creating WorkItems that are visible in Polarion Documents requires a **mandatory two-step process**. This specification documents the correct implementation based on extensive testing and analysis of the Polarion REST API v1.

**Critical Finding:** WorkItems created via API initially land in the document's "Recycle Bin" and require a second API call to become visible in the document structure.

## The Two-Step Process (MANDATORY)

### Step 1: Create WorkItem with Module Relationship
```python
POST /polarion/rest/v1/projects/{projectId}/workitems
```

**Request Body:**
```json
{
  "data": [{
    "type": "workitems",
    "attributes": {
      "type": "requirement",  // WorkItem type
      "title": "My Requirement",
      "description": {
        "type": "text/html",
        "value": "<p>Description</p>"
      },
      "status": "draft"
    },
    "relationships": {
      "module": {
        "data": {
          "type": "documents",
          "id": "ProjectId/SpaceId/DocumentName"  // CRITICAL: Correct format
        }
      }
    }
  }]
}
```

**Result:** WorkItem is created but appears in document's "Recycle Bin"

### Step 2: Add WorkItem to Document Content (CRITICAL!)
```python
POST /polarion/rest/v1/projects/{projectId}/spaces/{spaceId}/documents/{documentName}/parts
```

**Request Body:**
```json
{
  "data": [{
    "type": "document_parts",
    "attributes": {
      "type": "workitem"
    },
    "relationships": {
      "workItem": {
        "data": {
          "type": "workitems",
          "id": "ProjectId/WORKITEM-ID"
        }
      }
    }
  }]
}
```

**Result:** WorkItem becomes visible in the document

## Critical Rules and Constraints

### 1. NEVER Set outlineNumber
- **Rule:** The `outlineNumber` field is READ-ONLY
- **Error if violated:** "Cannot modify read-only field(s): outlineNumber"
- **Correct approach:** Let Polarion assign outline numbers automatically

### 2. Document ID Format
- **Correct:** `"ProjectId/SpaceId/DocumentName"`
- **Wrong:** `"DocumentName"` or `"ProjectId/DocumentName"`
- **Example:** `"Python/Functional Layer/Functional Concept"`

### 3. URL Encoding for Spaces
- Spaces with special characters must be URL-encoded
- Example: `"Functional Layer"` → `"Functional%20Layer"`

### 4. WorkItem ID Format
- Full format: `"ProjectId/WORKITEM-ID"` (e.g., `"Python/PYTH-1234"`)
- Short format: `"PYTH-1234"` (only for some endpoints)

## Implementation Example

### Python Implementation with PolarionClient

```python
from polarion_api.client import PolarionClient

client = PolarionClient()

# Step 1: Create WorkItem
work_item_data = {
    "type": "workitems",
    "attributes": {
        "type": "requirement",
        "title": "New Safety Requirement",
        "description": {
            "type": "text/html",
            "value": "<p>The system shall provide emergency shutdown capability</p>"
        },
        "status": "draft",
        "severity": "must_have",
        "priority": "50.0"
    },
    "relationships": {
        "module": {
            "data": {
                "type": "documents",
                "id": "Python/Functional Layer/Functional Concept"
            }
        }
    }
}

# Create the WorkItem
result = client.create_work_item(
    project_id="Python",
    work_item_data=work_item_data
)

# Extract WorkItem ID
wi_id = result["data"][0]["id"]  # e.g., "Python/PYTH-1234"
print(f"Created WorkItem: {wi_id}")

# Step 2: Add to Document (CRITICAL - Without this, WorkItem stays in Recycle Bin!)
doc_result = client.add_work_item_to_document(
    project_id="Python",
    work_item_id=wi_id,
    space_id="Functional Layer",
    document_name="Functional Concept"
)

if "error" not in doc_result:
    print(f"✅ WorkItem {wi_id} is now visible in the document!")
else:
    print(f"❌ Failed to add to document: {doc_result['error']}")
```

## Advanced: Positioning WorkItems

### Adding at Specific Position
To insert a WorkItem after a specific document part:

```python
# Find the target position (e.g., after a specific heading)
doc_result = client.add_work_item_to_document(
    project_id="Python",
    work_item_id=wi_id,
    space_id="Functional Layer",
    document_name="Functional Concept",
    previous_part_id="heading_FCTS-9187"  # Insert after this part
)
```

### Creating Parent-Child Relationships
To make a WorkItem appear under a specific header:

```python
# Link to parent header (separate from document positioning)
POST /projects/{projectId}/workitems/{workItemId}/linkedworkitems

{
  "data": [{
    "type": "linkedworkitems",
    "attributes": {
      "role": "parent"
    },
    "relationships": {
      "workItem": {
        "data": {
          "type": "workitems",
          "id": "Python/FCTS-9187"  // Parent header WorkItem
        }
      }
    }
  }]
}
```

## Common Pitfalls and Solutions

### Pitfall 1: WorkItem Created but Not Visible
**Symptom:** WorkItem shows warning "This Work Item was unmarked in the Document"
**Cause:** Step 2 (Document Parts API) was not executed
**Solution:** Always execute both steps

### Pitfall 2: Trying to Set outlineNumber
**Symptom:** HTTP 400 "Cannot modify read-only field(s): outlineNumber"
**Cause:** Attempting to set outlineNumber during creation or update
**Solution:** Remove outlineNumber from request - Polarion manages it

### Pitfall 3: Wrong Document ID Format
**Symptom:** HTTP 404 or "Document not found"
**Cause:** Incorrect document ID format
**Solution:** Use full format: "ProjectId/SpaceId/DocumentName"

### Pitfall 4: Using PATCH on relationships
**Symptom:** HTTP 400 "Cannot modify read-only field(s)"
**Cause:** Trying to PATCH /relationships/linkedWorkItems
**Solution:** Use POST to /workitems/{id}/linkedworkitems instead

## Verification

### Check if WorkItem is Properly Integrated
```python
GET /projects/{projectId}/workitems/{workItemId}?fields[workitems]=@all

# Look for:
# 1. "outlineNumber" attribute (e.g., "FC-1.2-1")
# 2. "module" relationship pointing to correct document
# 3. "linkedWorkItems" for parent-child relationships
```

### Expected Response for Visible WorkItem:
```json
{
  "data": {
    "type": "workitems",
    "id": "Python/PYTH-1234",
    "attributes": {
      "title": "My Requirement",
      "outlineNumber": "FC-1.2-1",  // Present = visible in document
      "status": "draft"
    },
    "relationships": {
      "module": {
        "data": {
          "type": "documents",
          "id": "Python/Functional Layer/Functional Concept"
        }
      }
    }
  }
}
```

## Summary

1. **WorkItem creation is a TWO-STEP process** - both steps are MANDATORY
2. **Never set outlineNumber** - it's read-only and managed by Polarion
3. **Document Parts API call is CRITICAL** - without it, WorkItems remain in Recycle Bin
4. **Use correct ID formats** - ProjectId/SpaceId/DocumentName for documents
5. **URL encode spaces** in API paths when they contain special characters
6. **Parent-child relationships** are separate from document positioning

## Required Permissions

- `createWorkItem` - for Step 1
- `modifyContent` on target document - for Step 2
- `modifyWorkItem` - for creating relationships

## API Endpoints Reference

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create WorkItem | `/projects/{projectId}/workitems` | POST |
| Add to Document | `/projects/{projectId}/spaces/{spaceId}/documents/{documentName}/parts` | POST |
| Create Parent Link | `/projects/{projectId}/workitems/{workItemId}/linkedworkitems` | POST |
| Verify WorkItem | `/projects/{projectId}/workitems/{workItemId}` | GET |
| Get Document Parts | `/projects/{projectId}/spaces/{spaceId}/documents/{documentName}/parts` | GET |

## Testing Checklist

- [ ] WorkItem created successfully (HTTP 201)
- [ ] Document Part added successfully (HTTP 201)
- [ ] WorkItem has outlineNumber after both steps
- [ ] WorkItem visible in Polarion UI
- [ ] Parent-child relationships work if needed
- [ ] No "unmarked in Document" warning