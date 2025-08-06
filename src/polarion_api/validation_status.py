"""
Test Validation Status Tracking System

This module provides decorators and utilities to track which methods have been 
tested and validated against production Polarion.

Usage:
    from polarion_api.validation_status import tested, TestStatus
    
    @tested(
        status=TestStatus.PRODUCTION_VALIDATED,
        test_file="tests/moduletest/test_document_discovery.py",
        test_method="test_discover_all_documents_and_spaces",
        date="2025-08-06",
        notes="Successfully tested with Python project, found 4 spaces and 4 documents"
    )
    def discover_all_documents_and_spaces():
        ...
"""

from enum import Enum
from functools import wraps
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import inspect
import json
import os
from pathlib import Path


class TestStatus(Enum):
    """Test validation status levels."""
    NOT_TESTED = "not_tested"                    # Method not tested yet
    MOCK_TESTED = "mock_tested"                  # Only tested against mock
    PRODUCTION_TESTED = "production_tested"      # Tested against production but not validated
    PRODUCTION_VALIDATED = "production_validated" # Fully tested and validated against production
    DEPRECATED = "deprecated"                     # Method is deprecated
    BLOCKED = "blocked"                          # Testing blocked due to dependencies/issues


class ValidationRegistry:
    """Registry to track all validated methods."""
    
    _instance = None
    _validations: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, func: Callable, status: TestStatus, **metadata) -> None:
        """Register a method's validation status.
        
        Args:
            func: The function being registered
            status: The validation status
            **metadata: Additional metadata (test_file, test_method, date, notes, etc.)
        """
        module = inspect.getmodule(func).__name__
        func_name = func.__name__
        key = f"{module}.{func_name}"
        
        self._validations[key] = {
            "module": module,
            "function": func_name,
            "status": status.value,
            "file": inspect.getfile(func),
            "line": inspect.getsourcelines(func)[1],
            "registered_at": datetime.now().isoformat(),
            **metadata
        }
    
    def get_status(self, func_or_name: Any) -> Optional[Dict[str, Any]]:
        """Get validation status for a function.
        
        Args:
            func_or_name: Function object or string name (module.function)
            
        Returns:
            Validation metadata or None if not found
        """
        if isinstance(func_or_name, str):
            key = func_or_name
        else:
            module = inspect.getmodule(func_or_name).__name__
            key = f"{module}.{func_or_name.__name__}"
        
        return self._validations.get(key)
    
    def get_all_by_status(self, status: TestStatus) -> List[Dict[str, Any]]:
        """Get all methods with a specific status.
        
        Args:
            status: The test status to filter by
            
        Returns:
            List of validation metadata for matching methods
        """
        return [
            v for v in self._validations.values()
            if v["status"] == status.value
        ]
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics of validation statuses.
        
        Returns:
            Dictionary with counts per status
        """
        summary = {status.value: 0 for status in TestStatus}
        for validation in self._validations.values():
            summary[validation["status"]] += 1
        return summary
    
    def export_report(self, output_file: Optional[str] = None) -> str:
        """Export validation report to JSON file.
        
        Args:
            output_file: Path to output file (default: test_reports/validation_status.json)
            
        Returns:
            Path to the generated report
        """
        if output_file is None:
            output_dir = Path("test_reports")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"validation_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "validations": self._validations
        }
        
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
        
        return str(output_file)
    
    def print_report(self) -> None:
        """Print a formatted validation report to console."""
        print("\n" + "="*60)
        print("VALIDATION STATUS REPORT")
        print("="*60)
        
        # Summary
        summary = self.get_summary()
        print("\nSummary:")
        for status in TestStatus:
            count = summary[status.value]
            if count > 0:
                print(f"  {status.value:25} : {count}")
        
        # Detailed by status
        print("\n" + "-"*60)
        for status in [TestStatus.PRODUCTION_VALIDATED, TestStatus.PRODUCTION_TESTED, 
                      TestStatus.MOCK_TESTED, TestStatus.NOT_TESTED]:
            methods = self.get_all_by_status(status)
            if methods:
                print(f"\n{status.value.upper()}:")
                for method in methods:
                    print(f"  • {method['module']}.{method['function']}")
                    if method.get('test_file'):
                        print(f"    Test: {method['test_file']}")
                    if method.get('notes'):
                        print(f"    Notes: {method['notes']}")
        
        print("\n" + "="*60)


# Global registry instance
_registry = ValidationRegistry()


def tested(status: TestStatus = TestStatus.PRODUCTION_VALIDATED,
          test_file: Optional[str] = None,
          test_method: Optional[str] = None,
          date: Optional[str] = None,
          notes: Optional[str] = None,
          **kwargs) -> Callable:
    """Decorator to mark a method as tested and validated.
    
    Args:
        status: The validation status (default: PRODUCTION_VALIDATED)
        test_file: Path to the test file
        test_method: Name of the test method
        date: Date of validation (YYYY-MM-DD format)
        notes: Additional notes about the test
        **kwargs: Any additional metadata to store
        
    Example:
        @tested(
            status=TestStatus.PRODUCTION_VALIDATED,
            test_file="tests/test_documents.py",
            test_method="test_discover_all",
            date="2025-08-06",
            notes="Tested with Python project"
        )
        def my_method():
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Register the validation
        _registry.register(
            func, 
            status,
            test_file=test_file,
            test_method=test_method,
            date=date or datetime.now().strftime("%Y-%m-%d"),
            notes=notes,
            **kwargs
        )
        
        # Add attribute to function for runtime checking
        func.__validated__ = True
        func.__validation_status__ = status
        func.__validation_metadata__ = {
            "test_file": test_file,
            "test_method": test_method,
            "date": date,
            "notes": notes,
            **kwargs
        }
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_validation_status(func_or_name: Any) -> Optional[Dict[str, Any]]:
    """Get validation status for a function.
    
    Args:
        func_or_name: Function object or string name (module.function)
        
    Returns:
        Validation metadata or None if not found
    """
    return _registry.get_status(func_or_name)


def get_validation_report() -> Dict[str, Any]:
    """Get complete validation report.
    
    Returns:
        Dictionary containing summary and all validations
    """
    return {
        "summary": _registry.get_summary(),
        "validations": _registry._validations
    }


def print_validation_report() -> None:
    """Print formatted validation report to console."""
    _registry.print_report()


def export_validation_report(output_file: Optional[str] = None) -> str:
    """Export validation report to JSON file.
    
    Args:
        output_file: Path to output file
        
    Returns:
        Path to the generated report
    """
    return _registry.export_report(output_file)


# Test assertion helper for pytest
def assert_method_validated(func: Callable, expected_status: TestStatus = TestStatus.PRODUCTION_VALIDATED):
    """Assert that a method has been validated with expected status.
    
    Args:
        func: The function to check
        expected_status: Expected validation status
        
    Raises:
        AssertionError: If method is not validated or has different status
    """
    status = _registry.get_status(func)
    if not status:
        raise AssertionError(f"{func.__name__} is not registered as validated")
    
    if status["status"] != expected_status.value:
        raise AssertionError(
            f"{func.__name__} has status '{status['status']}', "
            f"expected '{expected_status.value}'"
        )