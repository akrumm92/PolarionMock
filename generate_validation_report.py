#!/usr/bin/env python3
"""
Generate validation status report for all tested methods.

This script scans the codebase and generates a report showing which methods
have been tested and validated against production Polarion.

Usage:
    python generate_validation_report.py [--format json|console|both] [--output filename]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from polarion_api.validation_status import (
    print_validation_report,
    export_validation_report,
    get_validation_report
)


def main():
    """Main entry point for validation report generator."""
    parser = argparse.ArgumentParser(
        description="Generate validation status report for tested methods"
    )
    parser.add_argument(
        "--format",
        choices=["json", "console", "both"],
        default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for JSON format (default: test_reports/validation_status_[timestamp].json)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output (only show file path)"
    )
    
    args = parser.parse_args()
    
    # Import all modules to register decorators
    # This ensures all @tested decorators are executed
    import src.polarion_api.documents
    import src.polarion_api.work_items
    import src.polarion_api.client
    
    if args.format in ["console", "both"] and not args.quiet:
        print_validation_report()
    
    if args.format in ["json", "both"]:
        report_path = export_validation_report(args.output)
        
        if args.quiet:
            print(report_path)
        else:
            print(f"\n✓ Validation report saved to: {report_path}")
            
            # Show quick summary
            report = get_validation_report()
            summary = report['summary']
            total = sum(summary.values())
            validated = summary.get('production_validated', 0)
            
            if total > 0:
                coverage = validated / total * 100
                print(f"✓ Coverage: {validated}/{total} methods ({coverage:.1f}%)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())