#!/usr/bin/env python
"""
Test runner script for Polarion Mock tests
Supports running tests against both mock and production environments
"""

import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_report_directory():
    """Create directory for test reports."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(f"test_reports/{timestamp}")
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def start_mock_server():
    """Start the mock server if not already running."""
    import requests
    
    mock_url = os.getenv("MOCK_URL", "http://localhost:5000")
    try:
        response = requests.get(f"{mock_url}/health", timeout=2)
        if response.status_code == 200:
            logger.info("Mock server already running")
            return None
    except requests.exceptions.RequestException:
        logger.info("Starting mock server...")
        
    # Start mock server in background
    process = subprocess.Popen(
        [sys.executable, "-m", "src.mock"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    import time
    for i in range(10):
        try:
            response = requests.get(f"{mock_url}/health", timeout=1)
            if response.status_code == 200:
                logger.info("Mock server started successfully")
                return process
        except:
            time.sleep(1)
    
    logger.error("Failed to start mock server")
    process.terminate()
    return None


def run_tests(env, test_path=None, extra_args=None):
    """Run pytest with specified environment."""
    report_dir = create_report_directory()
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "--env", env,
        "-v",
        f"--html={report_dir}/report.html",
        "--self-contained-html",
        f"--json-report-file={report_dir}/report.json",
    ]
    
    # Add coverage if requested
    if extra_args and "--coverage" in extra_args:
        cmd.extend([
            "--cov=src",
            f"--cov-report=html:{report_dir}/coverage",
            "--cov-report=term"
        ])
    
    # Add test path if specified
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    # Add any extra arguments
    if extra_args:
        cmd.extend([arg for arg in extra_args if arg != "--coverage"])
    
    logger.info(f"Running tests against {env} environment")
    logger.info(f"Command: {' '.join(cmd)}")
    
    # Run tests
    result = subprocess.run(cmd)
    
    logger.info(f"Test reports saved to: {report_dir}")
    return result.returncode


def compare_environments():
    """Run tests against both environments and compare results."""
    logger.info("Running comparison tests...")
    
    # Run against mock
    mock_report = create_report_directory()
    mock_result = run_tests("mock")
    
    # Run against production
    prod_report = create_report_directory()
    prod_result = run_tests("production")
    
    # TODO: Implement actual comparison logic
    logger.info("Comparison complete - check individual reports for details")
    
    return 0 if (mock_result == 0 and prod_result == 0) else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Polarion tests")
    parser.add_argument(
        "--env",
        choices=["mock", "production", "both"],
        default=os.getenv("POLARION_ENV", "mock"),
        help="Target environment (default: mock)"
    )
    parser.add_argument(
        "--test",
        help="Specific test file or directory to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--start-mock",
        action="store_true",
        help="Start mock server before running tests"
    )
    parser.add_argument(
        "--markers",
        "-m",
        help="Pytest markers to filter tests"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Open HTML report after tests"
    )
    
    args, unknown = parser.parse_known_args()
    
    # Start mock server if requested
    mock_process = None
    if args.start_mock or (args.env in ["mock", "both"]):
        mock_process = start_mock_server()
    
    try:
        # Run tests based on environment
        if args.env == "both":
            exit_code = compare_environments()
        else:
            extra_args = unknown
            if args.coverage:
                extra_args.append("--coverage")
            if args.markers:
                extra_args.extend(["-m", args.markers])
            
            exit_code = run_tests(args.env, args.test, extra_args)
        
        # Open HTML report if requested
        if args.html and exit_code == 0:
            reports = list(Path("test_reports").glob("*/report.html"))
            if reports:
                latest_report = max(reports, key=lambda p: p.stat().st_mtime)
                logger.info(f"Opening report: {latest_report}")
                subprocess.run(["open", str(latest_report)])  # macOS
                # For Linux: subprocess.run(["xdg-open", str(latest_report)])
                # For Windows: subprocess.run(["start", str(latest_report)], shell=True)
        
        return exit_code
        
    finally:
        # Stop mock server if we started it
        if mock_process:
            logger.info("Stopping mock server...")
            mock_process.terminate()
            mock_process.wait()


if __name__ == "__main__":
    sys.exit(main())