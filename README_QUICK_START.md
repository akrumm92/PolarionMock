# Polarion Mock - Quick Start Guide

## 🚀 Installation & Setup

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install minimal dependencies
pip install -r requirements-minimal.txt

# 4. Start the mock server
python3 -m src.mock
```

The server will start on http://localhost:5000

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

## 🧪 Testing the API

### List all projects
```bash
curl http://localhost:5000/polarion/rest/v1/projects
```

### List work items in a project
```bash
curl http://localhost:5000/polarion/rest/v1/projects/elibrary/workitems
```

### Get a specific document
```bash
curl http://localhost:5000/polarion/rest/v1/projects/elibrary/spaces/_default/documents/requirements
```

### Create a new work item
```bash
curl -X POST http://localhost:5000/polarion/rest/v1/projects/myproject/workitems \
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
curl "http://localhost:5000/polarion/rest/v1/projects/elibrary/workitems?query=module.id:elibrary/_default/requirements"
```

## 🔧 Configuration

Authentication is disabled by default for easy testing. To enable it:

1. Edit `.env` file
2. Set `DISABLE_AUTH=false`
3. Use Bearer token in requests:
   ```bash
   curl -H "Authorization: Bearer your-token" http://localhost:5000/polarion/rest/v1/projects
   ```

## 📝 Running Tests

```bash
# Run all tests against mock
python run_tests.py --env mock --start-mock

# Run specific test file
pytest tests/test_projects.py -v

# Run integration tests
pytest tests/test_integration.py -v -m mock_only
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
2. **Port already in use**: Change port in `.env` file (`MOCK_PORT=5001`)
3. **Import errors**: Ensure you're in the project root directory

## 📚 More Information

- Full API documentation: See Polarion REST API docs
- Project specification: `PROJECT_SPECIFICATION.md`
- Development guide: `CLAUDE.md`