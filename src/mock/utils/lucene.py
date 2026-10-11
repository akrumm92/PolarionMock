"""
A small Lucene subset for the ``query`` parameter of list endpoints.

Supported: terms joined by whitespace or ``AND``; ``field:value`` matches one
attribute, a bare ``value`` matches any string attribute; ``*`` and ``?`` are
wildcards; ``"quoted values"``; matching ignores case. A list attribute
matches when one of its entries matches.

Anything else (``OR``, ``NOT``, parentheses, ranges) is refused with 400
instead of being ignored: a query the mock cannot evaluate must not return a
wrong result.
"""

import re
from fnmatch import fnmatchcase
from typing import Any, Dict, List, Optional, Tuple

from ..middleware.error_handler import ValidationError

_TERM = re.compile(r'(?:([\w.]+):)?("([^"]*)"|[^\s"]+)')
_UNSUPPORTED = re.compile(r"[()\[\]{}]|(?:^|\s)(?:OR|NOT)(?:\s|$)|(?:^|\s)[-+!]")


def parse(query: Optional[str]) -> List[Tuple[Optional[str], str]]:
    """``query`` as ``[(field or None, value), ...]``; empty for no query."""
    text = (query or "").strip()
    if not text:
        return []
    if _UNSUPPORTED.search(text):
        raise ValidationError(
            f"Query '{text}' uses syntax the mock does not support "
            "(only AND-joined field:value terms)"
        )
    terms = []
    for match in _TERM.finditer(text):
        field, raw, quoted = match.group(1), match.group(2), match.group(3)
        if field is None and raw == "AND":
            continue
        terms.append((field, (quoted if quoted is not None else raw).lower()))
    return terms


def _matches_value(value: Any, pattern: str) -> bool:
    if isinstance(value, (list, tuple)):
        return any(_matches_value(item, pattern) for item in value)
    if isinstance(value, dict):
        return _matches_value(value.get("value") or value.get("id"), pattern)
    if value is None:
        return False
    if isinstance(value, bool):
        value = "true" if value else "false"
    return fnmatchcase(str(value).lower(), pattern)


def matches(attributes: Dict[str, Any], query: Optional[str]) -> bool:
    """True when every term of ``query`` matches ``attributes``."""
    for field, pattern in parse(query):
        if field is None:
            if not any(
                _matches_value(v, pattern)
                for v in attributes.values()
                if isinstance(v, str)
            ):
                return False
        elif not _matches_value(attributes.get(field), pattern):
            return False
    return True
