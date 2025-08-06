"""
Test the validation status tracking system.

This test demonstrates how to use the validation status system and 
generates a validation report.
"""

import pytest
import json
from pathlib import Path

from src.polarion_api.validation_status import (
    TestStatus,
    get_validation_status,
    get_validation_report,
    print_validation_report,
    export_validation_report,
    assert_method_validated
)
from src.polarion_api.documents import DocumentsMixin


class TestValidationStatus:
    """Test validation status tracking system."""
    
    def test_discover_method_is_validated(self):
        """Test that discover_all_documents_and_spaces is marked as validated."""
        # Get the method
        method = DocumentsMixin.discover_all_documents_and_spaces
        
        # Check that it has validation attributes
        assert hasattr(method, '__validated__')
        assert method.__validated__ is True
        assert method.__validation_status__ == TestStatus.PRODUCTION_VALIDATED
        
        # Check metadata
        metadata = method.__validation_metadata__
        assert metadata['test_file'] == "tests/moduletest/test_document_discovery.py"
        assert metadata['date'] == "2025-08-06"
        assert "Python project" in metadata['notes']
    
    def test_get_validation_status(self):
        """Test retrieving validation status."""
        # Get status by method name
        status = get_validation_status("src.polarion_api.documents.discover_all_documents_and_spaces")
        
        assert status is not None
        assert status['status'] == TestStatus.PRODUCTION_VALIDATED.value
        assert status['function'] == 'discover_all_documents_and_spaces'
    
    def test_validation_report(self):
        """Test generating validation report."""
        report = get_validation_report()
        
        # Check summary
        assert 'summary' in report
        assert 'validations' in report
        
        # Check that we have at least one validated method
        summary = report['summary']
        assert summary.get('production_validated', 0) >= 1
        
        # Find our validated method
        validations = report['validations']
        discover_key = "src.polarion_api.documents.discover_all_documents_and_spaces"
        
        assert discover_key in validations
        validation = validations[discover_key]
        assert validation['status'] == 'production_validated'
        assert validation['test_file'] == "tests/moduletest/test_document_discovery.py"
    
    def test_export_validation_report(self, tmp_path):
        """Test exporting validation report to JSON."""
        # Export to temporary file
        output_file = tmp_path / "validation_report.json"
        exported_path = export_validation_report(str(output_file))
        
        assert Path(exported_path).exists()
        
        # Load and verify the exported report
        with open(exported_path, 'r') as f:
            report = json.load(f)
        
        assert 'generated_at' in report
        assert 'summary' in report
        assert 'validations' in report
        
        # Verify our method is in the report
        discover_key = "src.polarion_api.documents.discover_all_documents_and_spaces"
        assert discover_key in report['validations']
    
    def test_assert_method_validated(self):
        """Test validation assertion helper."""
        # This should pass
        assert_method_validated(
            DocumentsMixin.discover_all_documents_and_spaces,
            TestStatus.PRODUCTION_VALIDATED
        )
        
        # This should fail with wrong status
        with pytest.raises(AssertionError):
            assert_method_validated(
                DocumentsMixin.discover_all_documents_and_spaces,
                TestStatus.NOT_TESTED
            )
    
    def test_print_validation_report(self, capsys):
        """Test printing validation report to console."""
        print_validation_report()
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that report contains expected sections
        assert "VALIDATION STATUS REPORT" in output
        assert "Summary:" in output
        assert "production_validated" in output
        assert "discover_all_documents_and_spaces" in output


@pytest.mark.integration
def test_generate_validation_report():
    """Generate and save a validation report for documentation."""
    # Generate report
    output_dir = Path("test_reports")
    output_dir.mkdir(exist_ok=True)
    
    report_path = export_validation_report()
    print(f"\nValidation report saved to: {report_path}")
    
    # Also print to console
    print_validation_report()
    
    # Load and display key statistics
    with open(report_path, 'r') as f:
        report = json.load(f)
    
    summary = report['summary']
    total_methods = sum(summary.values())
    validated = summary.get('production_validated', 0)
    
    print(f"\nValidation Coverage:")
    print(f"  Total tracked methods: {total_methods}")
    print(f"  Production validated: {validated}")
    if total_methods > 0:
        print(f"  Coverage: {validated/total_methods*100:.1f}%")
    
    return report_path


if __name__ == "__main__":
    # Run this directly to generate a validation report
    print("Generating validation status report...")
    report_path = test_generate_validation_report()
    print(f"\nReport saved to: {report_path}")