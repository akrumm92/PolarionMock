# Test Data Input Files

This directory contains example input files for testing the Polarion API client.

## Work Item Files

### workitems_create.json
Example work items for creation:
- Requirement with full attributes
- Simple task
- Defect with HTML description

### workitems_update.json
Example attributes for updating work items:
- Status changes
- Priority updates
- Custom fields

### workitems_functional_safety.json
Specialized functional safety requirement:
- ASIL level tracking
- Safety goals
- Verification relationships

## Document Files

### documents_create.json
Example documents for creation:
- Requirements specification
- Test specification  
- Generic design document

### documents_update.json
Example attributes for updating documents:
- Title changes
- Status updates
- Home page content updates

## Usage

These files can be used with the polarion_api module:

```python
from polarion_api import PolarionClient

client = PolarionClient()

# Create work item from file
work_item = client.create_work_item(
    project_id="myproject",
    from_file="workitems_create.json"
)

# Create document from file
document = client.create_document(
    project_id="myproject",
    from_file="documents_create.json"
)

# Update work item from file
client.update_work_item(
    work_item_id="myproject/REQ-123",
    from_file="workitems_update.json"
)
```

## Format

All files follow the JSON:API specification format with:
- `attributes`: Resource attributes
- `relationships`: Optional relationships to other resources

The files can contain single objects or arrays of objects.