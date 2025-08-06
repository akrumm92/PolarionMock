# Mock Implementation Requirements

Based on actual Polarion REST API v1 behavior discovered through testing (August 2025).

## Table of Contents
1. [API Structure and Routing](#api-structure-and-routing)
2. [Work Items Endpoint](#work-items-endpoint)
3. [Document Discovery Pattern](#document-discovery-pattern)
4. [Header Requirements](#header-requirements)
5. [Error Responses](#error-responses)
6. [Data Models](#data-models)
7. [Mock-Specific Features](#mock-specific-features)

---

## API Structure and Routing

### Base URL Pattern
```
https://{host}/polarion/rest/v1/{endpoint}
```

### Critical URL Building Requirement
- **The base URL MUST end with trailing slash** for proper `urljoin()` behavior
- Example: `https://host/polarion/rest/v1/` ✓ (not `https://host/polarion/rest/v1` ✗)
- Client code uses `urljoin(base_url, endpoint)` which behaves differently with/without trailing slash

### Existing Endpoints (Confirmed)
```
GET  /polarion/rest/v1/projects/{projectId}/workitems
GET  /polarion/rest/v1/projects/{projectId}/workitems/{workItemId}
POST /polarion/rest/v1/projects/{projectId}/workitems
```

### Non-Existent Endpoints (Return 404)
```
GET /polarion/rest/v1/projects/{projectId}/documents  # DOES NOT EXIST
GET /polarion/rest/v1/projects/{projectId}/spaces     # DOES NOT EXIST
```

---

## Work Items Endpoint

### GET /projects/{projectId}/workitems

#### Request Parameters
```python
{
    "page[size]": 100,              # Max 100 per page
    "page[number]": 1,               # 1-based pagination
    "fields[workitems]": "@all",    # Include all work item fields
    "fields[documents]": "@all",    # Include document fields in relationships
    "include": "module",             # Include related resources
    "query": "HAS_VALUE:module"      # Filter for items with modules (optional)
}
```

#### Response Structure
```json
{
  "links": {
    "self": "current page URL",
    "first": "first page URL",
    "next": "next page URL or null",
    "last": "last page URL",
    "portal": "Polarion web UI URL"
  },
  "data": [
    {
      "type": "workitems",
      "id": "Python/FCTS-9345",
      "attributes": {
        "id": "FCTS-9345",
        "outlineNumber": "FC-4.1.1-3",
        "type": "technicalrequirement",
        "title": "Functional Safety Requirement 1",
        "description": {
          "type": "text/html",
          "value": "Safety Attributes need to be filled out"
        },
        "severity": "not_applicable",
        "priority": "50.0",
        "status": "proposed",
        "created": "2025-01-24T11:35:18.947Z",
        "updated": "2025-07-25T12:46:37.655Z"
      },
      "relationships": {
        "project": {
          "data": {
            "type": "projects",
            "id": "Python"
          }
        },
        "author": {
          "data": {
            "type": "users",
            "id": "I012062"
          }
        },
        "module": {
          "data": {
            "type": "documents",
            "id": "Python/Functional Layer/Functional Concept"
          }
        }
      }
    }
  ],
  "included": []
}
```

### Pagination Behavior
1. **Default page size**: 100 items
2. **Page numbering**: 1-based (starts at 1, not 0)
3. **Links**:
   - `next`: null when on last page
   - `first`/`last`: Always present
   - URLs must include all original query parameters

### Module Relationship (CRITICAL)
The `module` relationship contains document references:
```json
"module": {
  "data": {
    "type": "documents",
    "id": "projectId/spaceId/documentId"
  }
}
```

**Pattern**: `{projectId}/{spaceId}/{documentId}`
- Project ID: First segment
- Space ID: Second segment (can contain spaces, e.g., "Functional Layer")
- Document ID: Third segment

---

## Document Discovery Pattern

Since there's no direct documents endpoint, documents are discovered through work items:

### Real Data Example (Python Project)
```
Spaces found (4):
- Component Layer
- Domain Layer  
- Functional Layer
- Product Layer

Documents found (4):
- Python/Component Layer/Component Requirement Specification
- Python/Domain Layer/Software Requirement Specification
- Python/Functional Layer/Functional Concept
- Python/Product Layer/Product Requirements Specification
```

### Mock Implementation Requirements
1. **Every work item SHOULD have a module relationship** (100% in real data)
2. **Document IDs follow strict pattern**: `project/space/document`
3. **Spaces can contain spaces in names** (e.g., "Functional Layer")
4. **Multiple work items can reference the same document**

---

## Header Requirements

### Required Headers
```http
Authorization: Bearer {token}
Accept: */*                    # MUST be wildcard!
Content-Type: application/json
```

### Common Errors
- **406 Not Acceptable**: When `Accept` header is not `*/*`
- Mock MUST validate Accept header and return 406 if not wildcard

---

## Error Responses

### 404 Not Found
```json
{
  "errors": [{
    "status": "404",
    "title": "Not Found",
    "detail": "The requested resource [/polarion/rest/projects/Python/workitems] is not available"
  }]
}
```

### 406 Not Acceptable
```json
{
  "errors": [{
    "status": "406",
    "title": "Not Acceptable",
    "detail": "Accept header must be '*/*'"
  }]
}
```

### 401 Unauthorized
```json
{
  "errors": [{
    "status": "401",
    "title": "Unauthorized",
    "detail": "Invalid or missing authorization token"
  }]
}
```

---

## Data Models

### Work Item Types (Found in Real Data)
- `technicalrequirement`
- `functionalrequirement`
- `componentrequirement`
- `softwarerequirement`

### Work Item Status Values
- `proposed`
- `approved`
- `implemented`
- `verified`

### Priority Format
- String with decimal: `"50.0"`, `"100.0"`

### Date Format
- ISO 8601 with milliseconds: `"2025-01-24T11:35:18.947Z"`

### Description Format
Always an object:
```json
{
  "type": "text/html",
  "value": "<p>HTML content</p>"
}
```

---

## Mock-Specific Features

### Test Data Setup

#### Project Structure
```python
MOCK_PROJECT_STRUCTURE = {
    "Python": {
        "spaces": [
            "Component Layer",
            "Domain Layer",
            "Functional Layer",
            "Product Layer"
        ],
        "documents": {
            "Component Layer": ["Component Requirement Specification"],
            "Domain Layer": ["Software Requirement Specification"],
            "Functional Layer": ["Functional Concept"],
            "Product Layer": ["Product Requirements Specification"]
        }
    }
}
```

#### Work Item Generation
1. **Create 100+ work items** for pagination testing
2. **Assign each to a document** via module relationship
3. **Distribute across documents** (some documents get more items)
4. **Use realistic IDs**: `{PROJECT}-{NUMBER}` (e.g., "FCTS-9345")

### Mock Endpoints to Implement

#### Required (Priority 1)
```python
# Work Items
@app.route('/polarion/rest/v1/projects/<project_id>/workitems', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>/workitems/<item_id>', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>/workitems', methods=['POST'])
@app.route('/polarion/rest/v1/projects/<project_id>/workitems/<item_id>', methods=['PATCH'])

# Projects
@app.route('/polarion/rest/v1/projects', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>', methods=['GET'])
```

#### Return 404 (Priority 2)
```python
# These should explicitly return 404
@app.route('/polarion/rest/v1/projects/<project_id>/documents', methods=['GET'])
def documents_not_implemented(project_id):
    return jsonify({
        "errors": [{
            "status": "404",
            "title": "Not Found",
            "detail": f"The requested resource [/polarion/rest/v1/projects/{project_id}/documents] is not available"
        }]
    }), 404
```

### Validation Requirements

1. **Accept Header Validation**
```python
def validate_accept_header():
    if request.headers.get('Accept') != '*/*':
        return jsonify({
            "errors": [{
                "status": "406",
                "title": "Not Acceptable",
                "detail": "Accept header must be '*/*'"
            }]
        }), 406
```

2. **Authorization Validation**
```python
def validate_authorization():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({
            "errors": [{
                "status": "401",
                "title": "Unauthorized",
                "detail": "Bearer token required"
            }]
        }), 401
```

3. **Pagination Validation**
```python
def validate_pagination(page_size, page_number):
    if page_size > 100:
        page_size = 100  # Cap at 100
    if page_number < 1:
        page_number = 1  # Minimum is 1
    return page_size, page_number
```

### URL Building in Mock
```python
# CRITICAL: Ensure trailing slash
BASE_URL = "http://localhost:5001/polarion/rest/v1/"

def build_url(endpoint):
    # Use urljoin correctly with trailing slash
    from urllib.parse import urljoin
    return urljoin(BASE_URL, endpoint.lstrip('/'))
```

---

## Testing Requirements

### Mock Validation Tests
1. **Test pagination**: Verify next/prev links work correctly
2. **Test module relationships**: All work items should have valid module.data.id
3. **Test document ID format**: Must match `project/space/document` pattern
4. **Test header validation**: 406 for wrong Accept header
5. **Test 404 responses**: For non-existent endpoints

### Data Consistency Tests
```python
def test_all_workitems_have_modules():
    """Every work item should have a module relationship."""
    response = client.get('/polarion/rest/v1/projects/Python/workitems')
    for item in response.json['data']:
        assert 'module' in item['relationships']
        assert 'data' in item['relationships']['module']
        assert 'id' in item['relationships']['module']['data']

def test_document_id_format():
    """Document IDs must follow project/space/document pattern."""
    response = client.get('/polarion/rest/v1/projects/Python/workitems')
    for item in response.json['data']:
        doc_id = item['relationships']['module']['data']['id']
        parts = doc_id.split('/')
        assert len(parts) == 3, f"Invalid document ID: {doc_id}"
```

---

## Implementation Checklist

### Phase 1: Core Structure
- [ ] Set up Flask routes with correct paths
- [ ] Implement header validation middleware
- [ ] Create base error response handlers
- [ ] Ensure BASE_URL has trailing slash

### Phase 2: Data Models
- [ ] Create WorkItem model with all required fields
- [ ] Create Document reference model
- [ ] Implement module relationship structure
- [ ] Set up test data for Python project

### Phase 3: Work Items Endpoint
- [ ] Implement GET /projects/{id}/workitems with pagination
- [ ] Add query parameter handling
- [ ] Implement field filtering
- [ ] Add module relationship to all items

### Phase 4: Error Handling
- [ ] Return 404 for /projects/{id}/documents
- [ ] Return 406 for incorrect Accept header
- [ ] Return 401 for missing auth
- [ ] Handle invalid project IDs

### Phase 5: Testing
- [ ] Test document discovery via work items
- [ ] Test pagination with 100+ items
- [ ] Test header validation
- [ ] Verify against production behavior

---

## Notes for Implementers

1. **DO NOT** implement `/projects/{id}/documents` - it doesn't exist in real Polarion
2. **ALWAYS** include module relationships in work items
3. **STRICTLY** follow the `project/space/document` ID pattern
4. **ENSURE** trailing slash in base URL configuration
5. **VALIDATE** Accept header is exactly `*/*`
6. **USE** 1-based pagination (start at page 1, not 0)
7. **INCLUDE** all query parameters in pagination links

---

## Reference Implementation

See `tests/moduletest/outputdata/` for real response examples:
- `workitems_response.json` - Actual work items response
- `discovered_documents.json` - Extracted documents and spaces
- `SwaggerUiResponse.json` - Full API response with 100 work items