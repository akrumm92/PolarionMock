# Production Testing Guide

## Discovery Tests - Find Available Resources

Before running tests, use discovery tests to find valid IDs in your Polarion instance:

### Run All Discovery Tests
```bash
# Requires only TEST_PROJECT_ID to be set
export TEST_PROJECT_ID=YourProject
python run_tests.py --env production --test tests/moduletest/test_discovery.py
```

### Run Specific Discovery Tests
```bash
# Discover all accessible projects
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_all_projects

# Discover documents in your project (tries common names)
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_sample_documents

# Discover work item types in your project
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_work_item_types

# NEW: Discover all spaces in your project
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_project_spaces

# NEW: List all documents in default space
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_documents_in_default_space

# NEW: Complete discovery - all documents in all spaces
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_all_documents_in_all_spaces
```

### Check Discovery Results
```bash
# View discovered projects
cat tests/moduletest/outputdata/discovery_all_projects.json

# View discovered documents
cat tests/moduletest/outputdata/discovery_sample_documents.json

# View work item types and sample IDs
cat tests/moduletest/outputdata/discovery_work_item_types.json

# NEW: View discovered spaces
cat tests/moduletest/outputdata/discovery_project_spaces.json

# NEW: View documents in default space
cat tests/moduletest/outputdata/discovery_documents_in_space.json

# NEW: View all documents across all spaces
cat tests/moduletest/outputdata/discovery_all_documents_all_spaces.json
```

## Quick Start

### 1. Set Required Environment Variables

Add these to your `.env` file:

```bash
# Core Configuration
POLARION_ENV=production
POLARION_PERSONAL_ACCESS_TOKEN=your-pat-token
POLARION_BASE_URL=https://your-polarion-instance.com

# Test Data IDs - Must point to real objects in your Polarion instance!
TEST_PROJECT_ID=YourProject
TEST_DOCUMENT_ID=YourProject/_default/requirements
TEST_WORK_ITEM_ID=YourProject/WI-123
TEST_SPACE_ID=_default

# Optional: For specific test scenarios
TEST_DOCUMENT_WITH_PARTS_ID=YourProject/_default/document-with-sections
TEST_DOCUMENT_WITH_WORKITEMS_ID=YourProject/_default/document-with-workitems

# Security Settings
POLARION_VERIFY_SSL=false  # Only if using self-signed certificates
ALLOW_DESTRUCTIVE_TESTS=false  # Keep false for production!
```

### 2. Run Tests

Since `ALLOW_DESTRUCTIVE_TESTS=false`, destructive tests are automatically skipped:

```bash
# Run all document tests (destructive ones will be skipped)
python run_tests.py --env production --test tests/moduletest/test_documents.py

# Run all work item tests
python run_tests.py --env production --test tests/moduletest/test_work_items.py

# Run specific test
python run_tests.py --env production --test tests/moduletest/test_documents.py::TestDocumentsMixin::test_get_document
```

### 3. Check Output

JSON responses are saved to: `tests/moduletest/outputdata/`

## Important Notes

1. **No need for `-m "not destructive"`** - The test framework automatically skips destructive tests when `ALLOW_DESTRUCTIVE_TESTS=false`

2. **Mock-only tests** - Tests marked with `@pytest.mark.mock_only` are automatically skipped in production

3. **Missing IDs** - Tests will skip with helpful messages if required TEST_* variables are not set

## Troubleshooting

### Tests Skip with "TEST_DOCUMENT_ID not set"
- Set the `TEST_DOCUMENT_ID` environment variable to a real document ID
- Format: `PROJECT/SPACE/DOCUMENT` (e.g., `MyProject/_default/requirements`)

### 404 Not Found Errors
- Verify the IDs in your environment variables exist in Polarion
- Check project access permissions for your PAT

### Output JSONs Not Created
- Check the `tests/moduletest/outputdata/` directory exists
- Ensure write permissions on the directory
- Look for errors in test output

## Example Session

```bash
# 1. Create .env file with your settings
cp .env.example .env
# Edit .env with your Polarion instance details

# 2. Source the environment
source .env

# 3. Run non-destructive tests
python run_tests.py --env production --test tests/moduletest/

# 4. View results
ls -la tests/moduletest/outputdata/*.json
cat tests/moduletest/outputdata/documents_get_document.json
```