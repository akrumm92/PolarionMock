# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PolarionMock is a comprehensive test and development framework for Siemens Polarion ALM that includes:
- A complete pytest-based mock of the Polarion REST API
- Automatic API specification extraction from Polarion
- Test-driven development with bidirectional testing (mock vs production)

## Project Status

This is currently a greenfield project with a detailed specification in PROJECT_SPECIFICATION.md. Implementation has not yet begun.

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

## Planned Technology Stack

- **Language**: Python 3.8+
- **Web Framework**: Flask with Flask-CORS and Flask-SocketIO
- **Testing**: pytest with extensive plugin ecosystem
- **API Format**: JSON:API specification
- **Documentation**: OpenAPI/Swagger

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the mock server
python -m src.mock.app
# Alternative: python -m src.mock.server (if server.py exists)

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
POLARION_API_URL             # Base URL for Polarion API
POLARION_API_KEY             # API authentication key
MOCK_PORT=5000              # Port for mock server
ENABLE_WEBSOCKET=true       # Enable WebSocket support
```

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
3. **Incremental development**: Make small, testable changes
4. **Mock-first**: Implement new features in mock before production tests

## Resources

- Polarion REST API Docs: `Input/docs/` (PDFs)
- Test examples: `tests/integration/`
- Mock implementation: `src/mock/`
- Response examples: `src/mock/mock_data/`