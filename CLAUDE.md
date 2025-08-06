# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PolarionMock is a comprehensive test and development framework for Siemens Polarion ALM that includes:
- A complete pytest-based mock of the Polarion REST API
- Automatic API specification extraction from Polarion
- Test-driven development with bidirectional testing (mock vs production)

## Project Status

This is currently a greenfield project with a detailed specification in PROJECT_SPECIFICATION.md. Implementation has not yet begun.

## Important Testing Note

**Polarion is NOT running on this Mac development machine.** All test results with the production Polarion instance are executed on a different Windows computer that has access to the internal Polarion server (polarion-d.claas.local). Test reports are then transferred to this repository for analysis. When analyzing test failures, remember that:
- The test execution happens remotely
- Network/firewall issues may affect test results
- The Polarion REST API may have different availability on the test machine

### Configuration Files - CRITICAL
- **On Windows test machine**: Uses `.env` file for ALL configuration
- **`.env.PolarionConfig` in this repo**: ONLY for documentation/reference - shows what the Windows .env SHOULD contain
- **IMPORTANT**: The `.env.PolarionConfig` file is NOT used during test execution!
- **To fix configuration issues**: The `.env` file on the Windows machine must be updated directly
- **DO NOT** modify conftest.py to load `.env.PolarionConfig` - tests MUST use the standard `.env` file

## Development Philosophy

### Core Principles
1. **Test-First Development**: Always write tests before implementation
2. **Mock Realism**: Mock must behave exactly like production Polarion
3. **Bidirectional Testing**: All tests must run on both mock and production
4. **Self-Documenting Code**: Clear code with comprehensive documentation

### Code Quality Standards
- **Type Hints**: Use everywhere possible for better IDE support and type safety
- **Docstrings**: Required for all public functions and classes
- **Error Handling**: Explicit and descriptive error messages
- **Logging**: Structured logging at appropriate levels

### Critical Implementation Guidelines

#### Pydantic v2 Compatibility
- Use `model_dump()` instead of `dict()` for Pydantic models
- Use `Literal` types instead of deprecated `const=True`
- Override `to_json_api()` in models that inherit from BaseResource to ensure proper JSON serialization

#### JSON Serialization
- All Pydantic model attributes must be properly serialized using `model_dump(exclude_none=True)`
- Custom models (WorkItem, Document, Project) need explicit `to_json_api()` methods
- Handle flexible input types (e.g., description can be string or dict)

#### Test Implementation
- Always import required modules: `os`, `json`, test helpers
- Use logging fixtures (`log_test_info`, `capture_api_calls`) for better debugging
- Handle authentication states properly (check `DISABLE_AUTH` environment variable)
- Tests must work with both mock and production environments

## Planned Technology Stack

- **Language**: Python 3.8+
- **Web Framework**: Flask with Flask-CORS and Flask-SocketIO
- **Testing**: pytest with extensive plugin ecosystem
- **API Format**: JSON:API specification
- **Documentation**: OpenAPI/Swagger

## Test Validation Tracking System

The project uses a decorator-based system to track which methods have been tested and validated against production Polarion.

### Using the @tested Decorator
```python
from polarion_api.validation_status import tested, TestStatus

@tested(
    status=TestStatus.PRODUCTION_VALIDATED,
    test_file="tests/moduletest/test_document_discovery.py",
    test_method="test_discover_all_documents_and_spaces",
    date="2025-08-06",
    notes="Successfully tested with Python project"
)
def my_method():
    pass
```

### Validation Status Levels
- `NOT_TESTED`: Method not tested yet
- `MOCK_TESTED`: Only tested against mock
- `PRODUCTION_TESTED`: Tested against production but not fully validated
- `PRODUCTION_VALIDATED`: Fully tested and validated against production ✓
- `DEPRECATED`: Method is deprecated
- `BLOCKED`: Testing blocked due to dependencies/issues

### Generate Validation Report
```bash
# Show validation report in console
python generate_validation_report.py --format console

# Export to JSON
python generate_validation_report.py --format json

# Both console and JSON
python generate_validation_report.py --format both

# Run validation status tests
pytest tests/moduletest/test_validation_status.py
```

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
# Or for minimal setup:
pip install -r requirements-minimal.txt

# Run the mock server
MOCK_PORT=5001 python -m src.mock

# Generate JWT token for authentication
python generate_token_auto.py

# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/api/  # API tests only
pytest tests/workflows/  # Workflow tests only
pytest -m integration  # Integration tests only
pytest -m "not slow"  # Skip slow tests

# Run tests against mock
export POLARION_ENV=mock && pytest
# Alternative: python run_tests.py --env mock

# Run tests against production
export POLARION_ENV=production && pytest
# Alternative: python run_tests.py --env production

# Document Discovery Test (primary test for spaces/documents)
python run_tests.py --env production --test tests/moduletest/test_document_discovery.py::TestDocumentDiscovery::test_discover_all_documents_and_spaces

# Extract from existing JSON (no API connection needed)
python tests/moduletest/test_extract_from_swagger_response.py

# Generate coverage report
python run_tests.py --coverage --html

# Analyze Swagger/OpenAPI spec
python AnalyseSwaggerUI/analyseSwaggerUi.py

# Code quality checks
black src tests  # Format code
flake8 src tests  # Lint code
mypy src  # Type checking
```

## Architecture

### Directory Structure
```
src/
├── mock/
│   ├── api/          # Flask routes and endpoints
│   ├── models/       # Data models
│   ├── middleware/   # Auth, rate limiting, logging
│   ├── storage/      # Data layer and fixtures
│   ├── websocket/    # WebSocket support
│   └── utils/        # Mock-specific utilities
└── utils/            # Shared utilities

tests/
├── api/              # Endpoint tests
├── workflows/        # Business process tests
├── contracts/        # API compliance tests
├── performance/      # Performance tests
├── security/         # Security tests
├── fixtures/         # Test data and fixtures
└── helpers/          # Test utilities

Additional directories:
├── docs/             # Documentation
├── scripts/          # Utility scripts
├── dashboard/        # Real-time test dashboard
└── Input/            # API specifications and docs (user-provided)
```

### Test Organization Example
```python
# Test structure pattern
@pytest.mark.integration  # Always use markers
class TestWorkItems:
    """Tests that work on both Mock and Production"""
    
    def test_create_work_item(self, polarion_client):
        # Test implementation
        pass

@pytest.mark.mock_only  # For mock-specific tests
def test_mock_reset():
    pass
```

### Key Implementation Phases

1. **Phase 1**: API Integration - Extract and document Polarion API
2. **Phase 2**: Mock Development - Build Flask-based mock server
3. **Phase 3**: Test Development - Create comprehensive test suite
4. **Phase 4**: Verification - Ensure mock/production parity
5. **Phase 5**: Continuous Improvement - Refine based on test feedback

## Important Considerations

- The mock must maintain 100% API compatibility with Polarion
- Tests should run identically against mock and production
- WebSocket support is required for real-time features
- Performance metrics and gap analysis are core features
- Authentication should simulate Polarion's behavior

## Getting Started

Before implementing, review PROJECT_SPECIFICATION.md thoroughly as it contains:
- Detailed API endpoint specifications
- Response format examples
- Test categories and strategies
- Performance requirements
- Security considerations

## Working with API Specifications

When working with Polarion API:
1. API specifications are provided in the Input/ directory
2. Generate mock endpoints from the specification
3. Validate all data types against schemas
4. Consider versioning and deprecations

## Mock Development Guidelines

When extending the mock:
1. Study real API behavior first
2. Implement realistic delays
3. Simulate edge cases and errors
4. Use existing response builders in src/mock/utils/

## Test Development Guidelines

When writing tests:
1. Use fixtures from conftest.py
2. Write parametrized tests where appropriate
3. Test both happy path and error cases
4. Document special Polarion behaviors

## Environment Variables

```bash
POLARION_ENV=mock|production  # Target environment for tests
POLARION_BASE_URL            # Base URL for Polarion (e.g., https://polarion.example.com)
POLARION_REST_V1_PATH=/polarion/rest/v1  # Path to REST API v1 (default shown)
POLARION_API_PATH=/polarion/api          # Path to legacy API (default shown)
POLARION_PERSONAL_ACCESS_TOKEN  # Personal Access Token for API authentication
POLARION_VERIFY_SSL=true|false  # SSL certificate verification (false for self-signed)
MOCK_PORT=5001              # Port for mock server (5001 to avoid macOS AirPlay conflicts)
ENABLE_WEBSOCKET=true       # Enable WebSocket support
DISABLE_AUTH=true|false     # Disable authentication for development (default: false)
JWT_SECRET_KEY              # Secret key for signing JWT tokens (any string)
MOCK_AUTH_TOKEN            # JWT token for mock API authentication
```

## Critical Polarion API Information

### Headers Required for Polarion REST API v1:
```python
headers = {
    'Authorization': f'Bearer {pat}',
    'Accept': '*/*',  # MUST use wildcard - Polarion returns 406 with other values!
    'Content-Type': 'application/json'
}
```

### Two Different Endpoints:
1. `/polarion/api` - Legacy API, returns HTML, used for auth testing
2. `/polarion/rest/v1` - Main REST API, returns JSON:API format

### Space and Document Discovery - CRITICAL:
**Polarion REST API has NO direct endpoint for listing documents or spaces!** 

#### How to discover documents and spaces:
1. **Primary method**: Use Work Items API with module relationships
   ```python
   # Fetch work items from /projects/{projectId}/workitems
   # Extract document IDs from module.data.id
   # Format: "projectId/spaceId/documentId"
   ```
2. **The `/projects/{projectId}/documents` endpoint does NOT exist**
3. **Use the `discover_all_documents_and_spaces()` method in `documents.py`**

#### Successfully tested discovery (August 2025):
- **Python project**: Found 4 spaces and 4 documents
  - Spaces: Component Layer, Domain Layer, Functional Layer, Product Layer
  - Documents: Component/Domain/Functional Requirement Specifications
  - 100% of work items had module relationships

### URL Building Bug Fix (CRITICAL):
**Problem**: `urljoin()` behavior with absolute paths
- When endpoint starts with `/`, urljoin treats it as absolute and replaces the entire path
- **Solution**: Ensure `rest_api_url` ends with `/` (implemented in `config.py:55-62`)
- **Example of the bug**:
  ```python
  # WRONG - loses /polarion/rest/v1
  urljoin('https://host/polarion/rest/v1', '/projects/id/workitems')
  # Result: https://host/projects/id/workitems ❌
  
  # CORRECT - preserves full path
  urljoin('https://host/polarion/rest/v1/', 'projects/id/workitems')
  # Result: https://host/polarion/rest/v1/projects/id/workitems ✅
  ```

### Common Issues:
- **406 Not Acceptable**: You're not using `Accept: */*` header
- **SSL Certificate errors**: Set `POLARION_VERIFY_SSL=false`
- **Connection refused**: Check if REST API is enabled in Polarion
- **404 on bulk endpoints**: Many bulk query endpoints don't exist in Polarion
- **404 on /polarion/rest/projects/{id}/workitems**: Check if POLARION_REST_V1_PATH includes `/v1`
- **Empty work items response**: Verify project ID is correct and work items exist

## Authentication

### Mock Server Authentication
- Uses JWT tokens for authentication (unlike production Polarion which uses PAT)
- Generate tokens with: `python generate_token_auto.py [username] [hours]`
- Tokens must be generated with the same JWT_SECRET_KEY that the server uses
- Set DISABLE_AUTH=true in .env for development without authentication

### Important: JWT_SECRET_KEY vs Token
- **JWT_SECRET_KEY**: A password/secret used to sign tokens (set in .env)
- **MOCK_AUTH_TOKEN**: The actual JWT token used by tests (generated using the secret)
- If you get "Signature verification failed", regenerate token with current JWT_SECRET_KEY

## Known Issues & Next Steps

### Known Issues
1. **API Specification**: Provided by user in Input/ directory
2. **Mock Persistence**: Currently only in-memory with file backup
3. **Test Isolation**: Some tests may affect each other
4. **WebSocket Support**: Not yet implemented

### Short-term Goals (Sprint 1)
- [ ] Extract API spec correctly
- [ ] Implement missing Work Item types in mock
- [ ] Add Document hierarchy support
- [ ] Test Management APIs

### Medium-term Goals (Sprint 2-3)
- [ ] WebSocket support for live updates
- [ ] Complete authentication implementation
- [ ] Performance test suite
- [ ] Coverage dashboard

### Long-term Goals (Sprint 4+)
- [ ] Polarion plugin development
- [ ] CI/CD integration
- [ ] Multi-version support
- [ ] Advanced performance optimization

## Helpful Tips

1. **Always check .env**: Many issues come from wrong environment variables
2. **Read logs**: Detailed logs in `test_reports/*/logs/`
   - `pytest.log`: Complete test execution log with DEBUG level
   - `environment.txt`: Test environment configuration
3. **Incremental development**: Make small, testable changes
4. **Mock-first**: Implement new features in mock before production tests
5. **Test with logging**: Use `python run_single_test.py <test_file>` for detailed logs
6. **Check reports**: HTML reports in `test_reports/*/report.html` show test results visually

## Key Implementation Files

### Document and Space Discovery
- **`src/polarion_api/documents.py:826-995`**: `discover_all_documents_and_spaces()` method
  - Fetches all work items with pagination
  - Extracts document IDs from module relationships
  - Saves `workitems_response.json` and `discovered_documents.json`
- **`tests/moduletest/test_document_discovery.py`**: Comprehensive test suite
- **`tests/moduletest/test_extract_from_swagger_response.py`**: Standalone extractor for saved JSON

### Configuration
- **`src/polarion_api/config.py`**: Configuration loading and URL building
  - CRITICAL: `rest_api_url` must end with `/` for proper urljoin behavior
- **`src/polarion_api/client.py`**: HTTP client with retry logic
  - Uses `urljoin()` to build URLs - be careful with leading slashes!

## Resources

- Polarion REST API Docs: `Input/docs/` (PDFs)
- Test examples: `tests/integration/`
- Mock implementation: `src/mock/`
- Response examples: `src/mock/mock_data/`
- **Mock Implementation Requirements**: `MOCK_IMPLEMENTATION_REQUIREMENTS.md` - Detailed requirements based on actual API behavior
- **Real API Responses**: `test_reports/20250806_101810/SwaggerUiResponse.json` - Actual Polarion responses