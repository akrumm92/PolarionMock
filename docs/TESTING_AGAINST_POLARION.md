# Testing Against Production Polarion

This guide explains how to run tests against your production Polarion instance.

## Prerequisites

1. **Polarion REST API** must be enabled on your server
2. **Personal Access Token (PAT)** with API access permissions
3. **Python environment** with dependencies installed

## Configuration

### 1. Update your `.env` file

```bash
# Set environment to production
POLARION_ENV=production

# Polarion connection settings
POLARION_BASE_URL=https://polarion-d.claas.local
POLARION_REST_V1_PATH=/polarion/rest/v1
POLARION_API_PATH=/polarion/api
POLARION_PERSONAL_ACCESS_TOKEN=your-actual-pat-here

# Disable SSL verification for self-signed certificates
POLARION_VERIFY_SSL=false

# Optional: Set a specific test project
TEST_PROJECT_ID=your-test-project-id
```

### 2. Test the connection

```bash
# Activate virtual environment
source venv/bin/activate

# Test connection to Polarion
python scripts/test_polarion_connection.py

# More detailed test with both endpoints
python scripts/test_polarion_dual_endpoints.py
```

## Running Tests

### Option 1: Using the test runner

```bash
# Run all tests against production
python run_tests.py --env production

# Run with coverage report
python run_tests.py --env production --coverage

# Run specific test category
python run_tests.py --env production --tests integration
```

### Option 2: Using pytest directly

```bash
# Set environment and run all tests
export POLARION_ENV=production
pytest

# Run specific test file
pytest tests/test_workitems.py -v

# Run specific test
pytest tests/test_workitems.py::test_list_work_items -v

# Skip mock-only tests
pytest -m "not mock_only"

# Run only integration tests
pytest -m integration
```

### Option 3: With explicit parameters

```bash
# Run with explicit endpoint
pytest --env production \
  --polarion-endpoint https://polarion-d.claas.local/polarion/rest/v1 \
  -v
```

## Important Notes

### Headers for Polarion REST API v1

Polarion's REST API v1 **requires** the Accept header to be `*/*`:

```python
headers = {
    'Authorization': f'Bearer {pat}',
    'Accept': '*/*',  # MUST be wildcard!
    'Content-Type': 'application/json'
}
```

Using other Accept headers like `application/json` or `application/vnd.api+json` will result in 406 "Not Acceptable" errors.

### Two Different Endpoints

1. **Legacy API** (`/polarion/api`): Returns HTML, used for auth testing
2. **REST API v1** (`/polarion/rest/v1`): Main API, returns JSON:API format

### Common Issues

1. **406 Not Acceptable**: You're not using `Accept: */*` header
2. **SSL Certificate Error**: Set `POLARION_VERIFY_SSL=false`
3. **401 Unauthorized**: Check your PAT is valid and has API permissions
4. **Connection Refused**: Verify REST API is enabled in Polarion

## Test Categories

### Basic Tests
```bash
# Project operations
pytest tests/test_projects.py --env production

# Work item operations  
pytest tests/test_workitems.py --env production

# Document operations
pytest tests/test_documents.py --env production
```

### Integration Tests
```bash
# Full workflows
pytest tests/test_integration.py --env production -m "not mock_only"
```

### Simple Examples
```bash
# Basic API examples
pytest tests/test_simple_examples.py --env production
```

## Verifying Results

After running tests, check:

1. **Test Report**: `test_reports/latest/report.html`
2. **Logs**: `test_reports/latest/logs/pytest.log`
3. **Coverage**: `test_reports/latest/coverage/index.html`

## Creating Test Data

When testing against production, be careful about creating test data:

1. Use a dedicated test project (set `TEST_PROJECT_ID`)
2. Use unique identifiers to avoid conflicts
3. Clean up test data after tests (if needed)

## Example Test Run

```bash
# 1. Set up environment
source venv/bin/activate
export POLARION_ENV=production

# 2. Verify connection
python scripts/test_polarion_connection.py

# 3. Run a simple test
pytest tests/test_projects.py::test_get_project -v

# 4. Run integration tests
pytest tests/test_integration.py -v -k "not mock_only"
```

## Debugging Failed Tests

If tests fail:

1. Check the detailed logs in `test_reports/*/logs/pytest.log`
2. Verify your PAT has necessary permissions
3. Check if the API endpoints exist in your Polarion version
4. Try the failed API call manually with curl:

```bash
# Example: List projects
curl -H "Authorization: Bearer YOUR_PAT" \
     -H "Accept: */*" \
     https://polarion-d.claas.local/polarion/rest/v1/projects
```