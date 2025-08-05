#!/usr/bin/env python
"""Debug script to check environment variables for tests."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tests"))

print("=" * 60)
print("ENVIRONMENT VARIABLE DEBUG")
print("=" * 60)

# Check all TEST_ variables
test_vars = {
    "TEST_PROJECT_ID": os.getenv("TEST_PROJECT_ID"),
    "POLARION_ENV": os.getenv("POLARION_ENV"),
    "POLARION_BASE_URL": os.getenv("POLARION_BASE_URL"),
    "POLARION_PERSONAL_ACCESS_TOKEN": os.getenv("POLARION_PERSONAL_ACCESS_TOKEN"),
    "TEST_DOCUMENT_ID": os.getenv("TEST_DOCUMENT_ID"),
    "TEST_WORK_ITEM_ID": os.getenv("TEST_WORK_ITEM_ID"),
}

print("\nEnvironment Variables:")
for key, value in test_vars.items():
    if value:
        if "TOKEN" in key:
            print(f"  {key} = ***hidden***")
        else:
            print(f"  {key} = {value}")
    else:
        print(f"  {key} = NOT SET")

# Test fixture logic
print("\n" + "=" * 60)
print("TESTING FIXTURE LOGIC")
print("=" * 60)

# Simulate the fixture logic
env_project_id = os.getenv("TEST_PROJECT_ID")
polarion_env = os.getenv("POLARION_ENV")

print(f"\nTEST_PROJECT_ID from env: {env_project_id}")
print(f"POLARION_ENV: {polarion_env}")

if env_project_id:
    print(f"✅ Would use TEST_PROJECT_ID: {env_project_id}")
elif polarion_env == "production":
    try:
        from tests.moduletest.test_config_production import PRODUCTION_PROJECTS
        default_id = PRODUCTION_PROJECTS.get("default", "myproject")
        print(f"⚠️  Would use from config file: {default_id}")
    except ImportError:
        print("❌ Would skip test - no TEST_PROJECT_ID set and config file not found")
else:
    print("✅ Would use default: myproject")

# Check .env file
print("\n" + "=" * 60)
print("CHECKING .env FILE")
print("=" * 60)

env_file = Path(".env")
if env_file.exists():
    print("✅ .env file exists")
    print("\nContents (TEST_ variables only):")
    with open(env_file, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "TEST_" in line:
                # Hide token values
                if "TOKEN" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        print(f"  {parts[0]}=***hidden***")
                else:
                    print(f"  {line.strip()}")
else:
    print("❌ No .env file found")
    print("  Create one by copying .env.example:")
    print("  cp .env.example .env")

print("\nDone!")