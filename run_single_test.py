#!/usr/bin/env python3
"""
Run a single test file with enhanced logging
Usage: python run_single_test.py tests/test_projects.py
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

def run_single_test(test_file):
    """Run a single test file with logging."""
    
    # Create test reports directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(f"test_reports/{timestamp}")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logs directory
    logs_dir = report_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Log file
    log_file = logs_dir / "pytest.log"
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v",
        "-s",  # No capture, show print statements
        "--log-cli-level=INFO",  # Show INFO logs in console
        f"--log-file={log_file}",
        "--log-file-level=DEBUG",
        f"--html={report_dir}/report.html",
        "--self-contained-html",
        f"--json-report-file={report_dir}/report.json",
        "--json-report-indent=2",
    ]
    
    print(f"Running test: {test_file}")
    print(f"Report directory: {report_dir}")
    print(f"Log file: {log_file}")
    print("-" * 80)
    
    # Run pytest
    result = subprocess.run(cmd)
    
    print("-" * 80)
    print(f"Test completed with exit code: {result.returncode}")
    print(f"Reports saved to: {report_dir}")
    print(f"View logs: cat {log_file}")
    print(f"View HTML report: open {report_dir}/report.html")
    
    return result.returncode

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_single_test.py <test_file>")
        print("Example: python run_single_test.py tests/test_projects.py")
        sys.exit(1)
    
    test_file = sys.argv[1]
    if not os.path.exists(test_file):
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    exit_code = run_single_test(test_file)
    sys.exit(exit_code)