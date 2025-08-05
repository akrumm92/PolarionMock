"""
Test to verify environment configuration is correct.
Run this before other tests to ensure setup is correct.
"""

import pytest
import os


class TestEnvironmentCheck:
    """Check that environment is properly configured."""
    
    @pytest.mark.integration
    def test_environment_variables(self):
        """Check that required environment variables are set."""
        print("\n" + "=" * 60)
        print("ENVIRONMENT CHECK")
        print("=" * 60)
        
        required_vars = {
            "POLARION_ENV": os.getenv("POLARION_ENV"),
            "TEST_PROJECT_ID": os.getenv("TEST_PROJECT_ID"),
        }
        
        optional_vars = {
            "POLARION_BASE_URL": os.getenv("POLARION_BASE_URL"),
            "POLARION_PERSONAL_ACCESS_TOKEN": os.getenv("POLARION_PERSONAL_ACCESS_TOKEN"),
            "TEST_DOCUMENT_ID": os.getenv("TEST_DOCUMENT_ID"),
        }
        
        print("\nRequired Variables:")
        missing = []
        for var, value in required_vars.items():
            if value:
                print(f"  ✅ {var} = {value}")
            else:
                print(f"  ❌ {var} = NOT SET")
                missing.append(var)
        
        print("\nOptional Variables:")
        for var, value in optional_vars.items():
            if value:
                if "TOKEN" in var:
                    print(f"  ✅ {var} = ***hidden***")
                else:
                    print(f"  ✅ {var} = {value}")
            else:
                print(f"  ⚠️  {var} = NOT SET")
        
        if missing:
            pytest.fail(f"Missing required environment variables: {', '.join(missing)}")
    
    @pytest.mark.integration
    def test_fixture_values(self, test_project_id, test_env):
        """Test that fixtures are returning correct values."""
        print("\n" + "=" * 60)
        print("FIXTURE VALUES")
        print("=" * 60)
        
        print(f"\ntest_env fixture: {test_env}")
        print(f"test_project_id fixture: {test_project_id}")
        
        env_test_project_id = os.getenv("TEST_PROJECT_ID")
        print(f"TEST_PROJECT_ID from env: {env_test_project_id}")
        
        if test_env == "production" and not test_project_id:
            pytest.fail("test_project_id fixture returned None for production environment")
        
        if env_test_project_id and test_project_id != env_test_project_id:
            pytest.fail(f"Fixture mismatch: fixture returned '{test_project_id}' but env has '{env_test_project_id}'")