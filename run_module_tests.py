#!/usr/bin/env python3
"""
Run polarion_api module tests with proper configuration.

This script helps run the module tests against either mock or production Polarion.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


def setup_environment(env_type: str):
    """Set up environment for testing."""
    print(f"Setting up environment for {env_type} testing...")
    
    # Set test environment
    os.environ["POLARION_ENV"] = env_type
    
    if env_type == "mock":
        # Ensure mock server settings
        os.environ.setdefault("MOCK_URL", "http://localhost:5001")
        os.environ.setdefault("MOCK_HOST", "0.0.0.0")
        os.environ.setdefault("MOCK_PORT", "5001")
        
        # Check if auth token exists
        if not os.environ.get("MOCK_AUTH_TOKEN"):
            print("No MOCK_AUTH_TOKEN found. Generating one...")
            try:
                result = subprocess.run(
                    [sys.executable, "generate_token_auto.py"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("Token generated successfully")
                else:
                    print(f"Warning: Failed to generate token: {result.stderr}")
            except Exception as e:
                print(f"Warning: Could not generate token: {e}")


def start_mock_server():
    """Start the mock server in background."""
    print("Starting mock server...")
    
    # Start mock server
    process = subprocess.Popen(
        [sys.executable, "-m", "src.mock"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    print("Waiting for mock server to be ready...")
    time.sleep(3)
    
    # Check if server is running
    import requests
    try:
        response = requests.get("http://localhost:5001/health", timeout=2)
        if response.status_code == 200:
            print("✓ Mock server is running")
            return process
        else:
            print(f"✗ Mock server returned status {response.status_code}")
            process.terminate()
            return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Mock server not responding: {e}")
        process.terminate()
        return None


def run_tests(args):
    """Run the tests with pytest."""
    # Build pytest command
    pytest_args = ["pytest", "tests/moduletest/"]
    
    # Add verbosity
    if args.verbose:
        pytest_args.append("-v")
    
    # Add stdout capture
    if args.capture_output:
        pytest_args.append("-s")
    
    # Add markers
    if args.unit_only:
        pytest_args.extend(["-m", "unit"])
    elif args.integration_only:
        pytest_args.extend(["-m", "integration"])
    
    # Add coverage
    if args.coverage:
        pytest_args.extend([
            "--cov=src/polarion_api",
            "--cov-report=html",
            "--cov-report=term"
        ])
    
    # Add specific test file
    if args.test_file:
        pytest_args = ["pytest", f"tests/moduletest/{args.test_file}"]
    
    # Add any additional pytest arguments
    if args.pytest_args:
        pytest_args.extend(args.pytest_args)
    
    print(f"\nRunning: {' '.join(pytest_args)}")
    print("-" * 80)
    
    # Run tests
    result = subprocess.run(pytest_args)
    
    return result.returncode


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run polarion_api module tests"
    )
    
    parser.add_argument(
        "--env",
        choices=["mock", "production"],
        default="mock",
        help="Test environment (default: mock)"
    )
    
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Don't start mock server (assume it's already running)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test output"
    )
    
    parser.add_argument(
        "-s", "--capture-output",
        action="store_true",
        help="Don't capture stdout/stderr"
    )
    
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Run only unit tests"
    )
    
    parser.add_argument(
        "--integration-only",
        action="store_true",
        help="Run only integration tests"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--test-file",
        help="Run specific test file (e.g., test_work_items.py)"
    )
    
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional arguments to pass to pytest"
    )
    
    args = parser.parse_args()
    
    # Setup environment
    setup_environment(args.env)
    
    # Start mock server if needed
    mock_process = None
    if args.env == "mock" and not args.no_server:
        mock_process = start_mock_server()
        if not mock_process:
            print("\n✗ Failed to start mock server")
            return 1
    
    try:
        # Run tests
        exit_code = run_tests(args)
        
        if args.coverage:
            print(f"\n✓ Coverage report generated in htmlcov/")
        
        return exit_code
        
    finally:
        # Stop mock server
        if mock_process:
            print("\nStopping mock server...")
            mock_process.terminate()
            mock_process.wait(timeout=5)
            print("✓ Mock server stopped")


if __name__ == "__main__":
    sys.exit(main())