"""
Production-specific test configuration.
Place real document and project IDs here for your Polarion instance.
"""

# Real project IDs that exist in your Polarion instance
PRODUCTION_PROJECTS = {
    "default": "Python",  # Change to an existing project
    "test": "TestProject",  # Change to your test project
}

# Real document IDs that exist in your Polarion instance
# Format: "project/space/document"
PRODUCTION_DOCUMENTS = {
    "requirements": "Python/_default/requirements",  # Change to existing document
    "test_spec": "Python/_default/test_specification",  # Change to existing document
}

# Real work item IDs for read-only tests
PRODUCTION_WORK_ITEMS = {
    "requirement": "Python/REQ-001",  # Change to existing work item
    "task": "Python/TASK-001",  # Change to existing work item
}

# Spaces that exist in your projects
PRODUCTION_SPACES = {
    "default": "_default",
    "custom": "my_space",  # Change if you have custom spaces
}