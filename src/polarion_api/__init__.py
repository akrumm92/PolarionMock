"""
Polarion API Client Library

A Python client library for interacting with the Polarion ALM REST API.
Supports work items, documents, projects, and more.
"""

from .client import PolarionClient
from .exceptions import (
    PolarionError,
    PolarionAuthError,
    PolarionNotFoundError,
    PolarionValidationError,
    PolarionServerError
)

__version__ = "0.1.0"
__all__ = [
    "PolarionClient",
    "PolarionError",
    "PolarionAuthError",
    "PolarionNotFoundError",
    "PolarionValidationError",
    "PolarionServerError"
]