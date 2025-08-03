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
- 🔐 Authentication simulation
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

# Install in development mode
pip install -e .
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Update `.env` with your Polarion credentials and preferences.

### Running the Mock Server

```bash
# Start the mock server
python -m src.mock.app

# Or use the CLI
polarion-mock serve --port 5000
```

### Running Tests

```bash
# Run all tests against mock
export POLARION_ENV=mock && pytest

# Run specific test categories
pytest tests/api/  # API tests only
pytest tests/workflows/  # Workflow tests only

# Run with coverage
pytest --cov=src --cov-report=html

# Run tests in parallel
pytest -n auto
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