# PolarionMock

A comprehensive mock and testing framework for Polarion ALM, providing:
- Complete pytest-based mock of Polarion REST API
- Bidirectional testing (mock vs production)
- Automatic API specification extraction

## Features

- 🚀 100% Polarion API coverage
- 🔄 Real-time WebSocket support
- 🧪 Comprehensive test suite with pytest
- 📊 Performance tracking and analysis
- 🔐 JWT-based authentication with token generator
- 📈 Real-time test execution dashboard

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/polarion-mock.git
cd polarion-mock

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# Or for minimal setup:
pip install -r requirements-minimal.txt

# Install in development mode
pip install -e .
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Update `.env` with your configuration:
   - **For Mock Testing**: No changes needed, just set `POLARION_ENV=mock`
   - **For Production Testing**: 
     - Set `POLARION_API_ENDPOINT` to your Polarion REST API URL (e.g., `https://polarion.example.com/polarion/rest/v1`)
     - Set `POLARION_PERSONAL_ACCESS_TOKEN` to your PAT (generated in Polarion user settings)

### Running the Mock Server

```bash
# Start the mock server (default port 5001)
MOCK_PORT=5001 python -m src.mock

# Or specify a different port
MOCK_PORT=8080 python -m src.mock
```

### Authentication

The mock server supports JWT-based authentication similar to production Polarion.

#### Quick Start:
```bash
# Option 1: Disable authentication for testing
# Edit .env and set: DISABLE_AUTH=true

# Option 2: Generate and use a token
python generate_token.py
# Copy the Bearer token and use in requests:
curl -H "Authorization: Bearer <TOKEN>" http://localhost:5001/polarion/rest/v1/projects
```

#### Configuration:
- `DISABLE_AUTH`: Set to `true` to disable authentication (default: `false`)
- `JWT_SECRET_KEY`: Secret key for JWT signing (default: `dev-secret-key`)

See [README_QUICK_START.md](README_QUICK_START.md) for detailed authentication examples.

### Running Tests

```bash
# Run all tests against mock with full logging
python run_tests.py --env mock

# Run a single test file with detailed logging
python run_single_test.py tests/test_projects.py

# Run specific test categories
pytest tests/api/  # API tests only
pytest tests/workflows/  # Workflow tests only

# Run with coverage
python run_tests.py --env mock --coverage

# View test results
ls -la test_reports/  # List all test runs
cat test_reports/*/logs/pytest.log  # View test logs
open test_reports/*/report.html  # View HTML report (macOS)
```

#### Test Logging

All tests automatically generate:
- **HTML Report**: `test_reports/<timestamp>/report.html`
- **JSON Report**: `test_reports/<timestamp>/report.json`
- **Detailed Logs**: `test_reports/<timestamp>/logs/pytest.log`
- **Environment Info**: `test_reports/<timestamp>/logs/environment.txt`

Logs include:
- API request/response details
- Test execution flow
- Assertions with actual vs expected values
- Performance metrics

### Polarion Integration

#### Testing Connection
```bash
# Test your Polarion connection with Personal Access Token
python scripts/test_polarion_connection.py
```

#### Extracting API Specification
```bash
# Analyze Polarion's OpenAPI/Swagger specification
python AnalyseSwaggerUI/analyseSwaggerUi.py
```

#### Personal Access Token (PAT)
1. Generate a PAT in Polarion:
   - Go to your Polarion user settings
   - Navigate to "Personal Access Tokens"
   - Create a new token with appropriate permissions

2. Configure in `.env`:
   ```
   POLARION_API_ENDPOINT=https://your-server.com/polarion/rest/v1
   POLARION_PERSONAL_ACCESS_TOKEN=your-token-here
   ```

## Project Structure

```
polarion-mock/
├── src/
│   ├── mock/           # Mock server implementation
│   │   ├── api/        # API endpoints
│   │   ├── models/     # Data models
│   │   ├── middleware/ # Auth, rate limiting, logging
│   │   ├── storage/    # Data persistence layer
│   │   └── websocket/  # WebSocket support
│   └── utils/          # Shared utilities
├── tests/              # Test suite
│   ├── api/            # API endpoint tests
│   ├── workflows/      # Business process tests
│   ├── contracts/      # API contract tests
│   └── performance/    # Performance tests
├── dashboard/          # Real-time test dashboard
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## Development

### Setting up pre-commit hooks

```bash
pre-commit install
```

### Running code quality checks

```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type checking
mypy src
```

### Building documentation

```bash
cd docs
make html
```

## Testing Strategy

The framework supports bidirectional testing:

1. **Mock Mode**: Tests run against the local mock server
2. **Production Mode**: Same tests run against real Polarion instance

This ensures the mock maintains 100% API compatibility.

## Dashboard

Access the real-time test execution dashboard:

```bash
python -m dashboard.app
```

Navigate to http://localhost:8050 to view:
- Test execution progress
- Performance metrics
- API coverage reports
- Mock vs production comparison

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built for Polarion ALM testing and development
- Inspired by best practices in API mocking and testing
- Powered by Flask, pytest, and the Python ecosystem


flowchart LR
  %% ==== Externe Systeme ====
  subgraph EXT[Externe Systeme]
    SRC[(PDF-Quelle\nFS / S3 / Share)]
    POL[Polarion\n(Project/WorkItems)]
  end

  %% ==== Pipeline (Luigi Task / Dagster Asset) ====
  subgraph PIPE[Pipeline (Luigi/Dagster)]
    INJ[Ingest PDFs]:::proc
    OCR[Text/OCR Extract]:::proc
    PARSE[Requirement Parser]:::proc
    NORM[Normalize & Split\n(ID, Title, Text, Priority)]:::proc
    VALID[Validate & Deduplicate\n(Schema/Links)]:::proc
    MAP[Map → Polarion Fields\n(type, title, description, custom)]:::proc
    PKG[Package JSON Payload]:::proc
    PUBL[Publish via MCP → Polarion]:::proc
    ACK[Writeback Status/IDs]:::proc
  end

  %% ==== Datenflüsse & Schnittstellen ====
  SRC  -- "PDF(A) Files" --> INJ
  INJ  -- "pdf_path list" --> OCR
  OCR  -- "raw_text.jsonl" --> PARSE
  PARSE -- "requirements.raw.json" --> NORM
  NORM -- "requirements.norm.json" --> VALID
  VALID -- "requirements.valid.json" --> MAP
  VALID -- "report.csv (Fehler)" --> ERR[Review Queue]:::aux
  MAP  -- "workitem[].fields" --> PKG
  PKG  -- "payload.json" --> PUBL
  PUBL -- "MCP Tool: polarion.publish\n(REST/SOAP unter der Haube)" --> POL
  PUBL -- "workitem_ids, status" --> ACK
  ACK  -- "Run Log / Metadata" --> STORE[(Logs/Metadata)]:::store

  %% ==== Styles ====
  classDef proc fill:#eef,stroke:#58f,stroke-width:1px,rx:6,ry:6;
  classDef ext fill:#ffd,stroke:#cc9,rx:6,ry:6;
  classDef store fill:#efe,stroke:#6c6,rx:6,ry:6;
  classDef aux fill:#fce,stroke:#d36,rx:6,ry:6;

  class SRC,POL ext;
  class STORE store;