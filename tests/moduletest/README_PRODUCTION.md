# Production Testing Guide

## Prerequisites

Before running tests against a production Polarion instance, you need to:

1. **Set Environment Variables**
```bash
# Required
export POLARION_ENV=production
export POLARION_PERSONAL_ACCESS_TOKEN="your-token-here"
export POLARION_BASE_URL="https://your-polarion-instance.com"

# Optional (for specific tests)
export TEST_PROJECT_ID="YourRealProjectID"
export TEST_DOCUMENT_ID="YourProject/_default/YourDocument"
export TEST_WORK_ITEM_ID="YourProject/WI-123"

# For self-signed certificates
export POLARION_VERIFY_SSL=false
```

2. **Update test_config_production.py**
Edit the file with real IDs from your Polarion instance:
```python
PRODUCTION_PROJECTS = {
    "default": "YourRealProject",
}

PRODUCTION_DOCUMENTS = {
    "requirements": "YourProject/_default/requirements",
}
```

## Running Non-Destructive Tests

### All non-destructive tests:
```bash
python run_tests.py --env production -m "not destructive"
```

### Specific test files:
```bash
# Documents (read-only)
python run_tests.py --env production --test tests/moduletest/test_documents.py -m "not destructive and not mock_only"

# Work Items (read-only)
python run_tests.py --env production --test tests/moduletest/test_work_items.py -m "not destructive"
```

### With specific IDs:
```bash
# Set test data
export TEST_DOCUMENT_ID="MyProject/_default/SRS"
export TEST_PROJECT_ID="MyProject"

# Run tests
python run_tests.py --env production --test tests/moduletest/test_documents.py::TestDocumentsMixin::test_get_document
```

## Common Issues

### 1. 404 Not Found Errors
- The document/project IDs don't exist in your Polarion instance
- Solution: Set correct TEST_DOCUMENT_ID and TEST_PROJECT_ID

### 2. Output files not created in correct location
- The save_response_to_json might be using wrong path on Windows
- Check: tests/moduletest/outputdata/ directory

### 3. SSL Certificate Errors
- Set POLARION_VERIFY_SSL=false for self-signed certificates

### 4. Authentication Errors
- Ensure POLARION_PERSONAL_ACCESS_TOKEN is valid
- Token needs read permissions for the projects/documents

## Example Test Run

```bash
# 1. Set up environment
export POLARION_ENV=production
export POLARION_PERSONAL_ACCESS_TOKEN="pat_xxxxx"
export POLARION_BASE_URL="https://polarion.company.com"
export TEST_PROJECT_ID="SOFTWARE"
export TEST_DOCUMENT_ID="SOFTWARE/_default/requirements"
export POLARION_VERIFY_SSL=false

# 2. Run specific non-destructive test
python run_tests.py --env production --test tests/moduletest/test_documents.py::TestDocumentsMixin::test_get_document

# 3. Check output
ls tests/moduletest/outputdata/documents_get_document.json
```