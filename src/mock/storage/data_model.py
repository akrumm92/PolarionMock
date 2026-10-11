"""
Enumerations and custom field definitions from the exported data model.

``docs/PolarionDataModel`` holds an XML export of a Polarion data model:
``enums/<name>-enum.xml`` (``<enumeration><option id=.. name=../>``) and
``custom fields/<type>-custom-fields.xml`` (``<fields><field id=.. type=../>``).
The enumeration endpoints answer from these files; ``MOCK_DATA_MODEL_DIR``
points at another export.

Only options that carry an ``id`` are served (an option without one cannot be
referenced through the API).
"""

import os
import xml.etree.ElementTree as ElementTree
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..middleware.error_handler import APIError

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_MODEL_DIR = _REPO_ROOT / "docs" / "PolarionDataModel"
DATA_MODEL_DIR_ENV = "MOCK_DATA_MODEL_DIR"

# option attribute in the export -> option key in the REST answer
_OPTION_KEYS = {
    "id": "id",
    "name": "name",
    "description": "description",
    "iconURL": "iconURL",
    "color": "color",
    "template": "templateWorkItem",
}
_FLAGS = ("default", "hidden", "terminal", "parent")


def data_model_dir() -> Path:
    configured = os.getenv(DATA_MODEL_DIR_ENV, "").strip()
    directory = Path(configured) if configured else DEFAULT_DATA_MODEL_DIR
    if not directory.is_dir():
        raise APIError(
            f"Polarion data model export not found at {directory} "
            f"(set {DATA_MODEL_DIR_ENV})",
            status_code=500,
        )
    return directory


def _option(element: ElementTree.Element) -> Dict[str, Any]:
    option: Dict[str, Any] = {}
    for attr, key in _OPTION_KEYS.items():
        if element.get(attr):
            option[key] = element.get(attr)
    for flag in _FLAGS:
        if element.get(flag) is not None:
            option[flag] = element.get(flag) == "true"
    return option


@lru_cache(maxsize=None)
def _enumeration(directory: Path, name: str) -> Optional[List[Dict[str, Any]]]:
    path = directory / "enums" / f"{name}-enum.xml"
    if not path.is_file():
        return None
    root = ElementTree.parse(path).getroot()
    elements = [e for e in root.iter("option") if e.get("id")]
    elements.sort(key=lambda e: int(e.get("sortOrder") or 0))
    return [_option(e) for e in elements]


def enumeration(name: str) -> Optional[List[Dict[str, Any]]]:
    """Options of enumeration ``name`` in export order, ``None`` if unknown."""
    return _enumeration(data_model_dir(), name)


@lru_cache(maxsize=None)
def _custom_fields(directory: Path, type_id: str) -> Dict[str, Dict[str, Any]]:
    path = directory / "custom fields" / f"{type_id}-custom-fields.xml"
    if not path.is_file():
        return {}
    root = ElementTree.parse(path).getroot()
    return {e.get("id"): dict(e.attrib) for e in root.iter("field") if e.get("id")}


def custom_fields(type_id: str) -> Dict[str, Dict[str, Any]]:
    """Custom field definitions of work item type ``type_id`` by field id."""
    return _custom_fields(data_model_dir(), type_id)
