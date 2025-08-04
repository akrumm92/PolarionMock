# Polarion Mock - Quick Start Guide

## 🚀 Installation & Setup

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install minimal dependencies
pip install -r requirements-minimal.txt

# 4. Start the mock server (port 5001 to avoid conflicts)
MOCK_PORT=5001 python3 -m src.mock
```

The server will start on http://localhost:5001

**Note**: Port 5000 is often used by macOS AirPlay. Use port 5001 or another port to avoid conflicts.

## 📋 What's Included

The mock server comes pre-loaded with dummy data:

### Projects
- **elibrary** - Electronic Library System
- **myproject** - Sample test project  
- **automotive** - Automotive safety requirements
- **medical** - Medical device compliance

### Documents
- Requirements specifications
- Test plans
- Architecture documents
- User stories

### Work Items
- 9 pre-configured work items of various types:
  - Requirements
  - Tasks
  - Defects
  - Test cases
  - User stories

## 🔐 Authentication Quick Start

**Note**: Authentication is currently enabled. You have two options:

### Option A: Disable Auth (Easiest for testing)
```bash
# Edit .env and set:
DISABLE_AUTH=true
# Restart the server
```

### Option B: Generate a Token
```bash
python generate_token.py
# Copy the Bearer token from output
```

## 🧪 Testing the API

**Note**: If authentication is enabled, add `-H "Authorization: Bearer <YOUR_TOKEN>"` to all curl commands.

### List all projects
```bash
# Without auth (if DISABLE_AUTH=true):
curl http://localhost:5001/polarion/rest/v1/projects

# With auth:
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://localhost:5001/polarion/rest/v1/projects
```

### List work items in a project
```bash
# Without auth:
curl http://localhost:5001/polarion/rest/v1/projects/elibrary/workitems

# With auth:
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://localhost:5001/polarion/rest/v1/projects/elibrary/workitems
```

### Get a specific document
```bash
# Without auth:
curl http://localhost:5001/polarion/rest/v1/projects/elibrary/spaces/_default/documents/requirements

# With auth:
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://localhost:5001/polarion/rest/v1/projects/elibrary/spaces/_default/documents/requirements
```

### Create a new work item
```bash
curl -X POST http://localhost:5001/polarion/rest/v1/projects/myproject/workitems \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "type": "workitems",
      "attributes": {
        "title": "New Feature Request",
        "type": "requirement",
        "status": "open",
        "priority": "high"
      }
    }]
  }'
```

### Query work items in a document
```bash
curl "http://localhost:5001/polarion/rest/v1/projects/elibrary/workitems?query=module.id:elibrary/_default/requirements"
```

## 🔧 Configuration

### Authentication

Authentication is currently **enabled** by default (`DISABLE_AUTH=false` in `.env`).

#### Option 1: Disable Authentication (for easy testing)
```bash
# Edit .env file and set:
DISABLE_AUTH=true
```

#### Option 2: Use Authentication Token

1. **Generate a token** using the provided script:
   ```bash
   source venv/bin/activate
   python generate_token.py
   # Enter user ID (default: admin)
   # Enter validity in hours (default: 24)
   ```

2. **Use the token** in your requests:
   ```bash
   # The script will output a Bearer token like:
   # Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   
   # Use it in curl:
   curl -H "Authorization: Bearer <YOUR_TOKEN>" http://localhost:5001/polarion/rest/v1/projects
   
   # Or set as environment variable:
   export AUTH_TOKEN="Bearer <YOUR_TOKEN>"
   curl -H "Authorization: $AUTH_TOKEN" http://localhost:5001/polarion/rest/v1/projects
   ```

3. **Configure JWT Secret** (optional):
   ```bash
   # In .env file:
   JWT_SECRET_KEY=your-secret-key-here
   ```

## 📝 Running Tests

### Against Mock Server

```bash
# Run all tests against mock
python run_tests.py --env mock --start-mock

# Run specific test file
pytest tests/test_projects.py -v

# Run integration tests
pytest tests/test_integration.py -v -m mock_only
```

### Against Production Polarion

See [TESTING_AGAINST_POLARION.md](docs/TESTING_AGAINST_POLARION.md) for detailed instructions.

Quick start:
```bash
# Set environment to production
export POLARION_ENV=production

# Run tests
pytest -v
```

## 🏗️ Project Structure

```
src/mock/
├── api/          # API endpoints
├── models/       # Data models
├── storage/      # Data store with dummy data
└── utils/        # Response builders

tests/
├── test_projects.py     # Project API tests
├── test_workitems.py    # Work Item API tests
├── test_documents.py    # Document API tests
└── test_integration.py  # Complete workflow tests
```

## 💡 Common Use Cases

### 1. Create a document with work items
See `test_complete_document_workflow` in `tests/test_integration.py`

### 2. Move work items between documents
See `test_workitem_move_between_documents` in `tests/test_integration.py`

### 3. Query work items by various criteria
- By type: `?query=type:requirement`
- By status: `?query=status:open`
- By document: `?query=module.id:project/space/document`

## 🐛 Troubleshooting

1. **Module not found errors**: Make sure virtual environment is activated
2. **Port already in use**: The server defaults to port 5001. Change with `MOCK_PORT=8080`
3. **Import errors**: Ensure you're in the project root directory
4. **PyJWT missing**: Run `pip install PyJWT==2.8.0`
5. **Pydantic errors**: Ensure you have pydantic>=2.10.6 for Python 3.13 support

## 📚 More Information

- Full API documentation: See Polarion REST API docs
- Project specification: `PROJECT_SPECIFICATION.md`
- Development guide: `CLAUDE.md`