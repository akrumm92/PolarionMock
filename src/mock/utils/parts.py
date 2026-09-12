"""
JSON:API rendering helpers for document parts, sparse fieldsets and
pagination links - shaped after the responses of a real Polarion server.

Real ``GET .../documents/{name}/parts?fields[document_parts]=@all`` answer::

    {
      "links": {"self": "...", "first": "...?page%5Bnumber%5D=1",
                "next": "...?page%5Bnumber%5D=2", "last": "...?page%5Bnumber%5D=3"},
      "data": [
        {"type": "document_parts",
         "id": "PROJ/Space Name/Document/heading_PROJ-1",
         "attributes": {"id": "heading_PROJ-1", "type": "heading",
                        "content": "<h1 id=\"polarion_wiki macro name=module-workitem;params=id=PROJ-1\"></h1>"},
         "relationships": {"workItem": {"data": {"type": "workitems", "id": "PROJ/PROJ-1"}}},
         "links": {"self": "https://host/polarion/rest/v1/projects/PROJ/spaces/Space%20Name/documents/Document/parts/heading_PROJ-1"}}
      ],
      "meta": {"totalCount": 218}
    }
"""

from typing import Any, Dict, List, Optional, Iterable, Tuple
from urllib.parse import quote, urlencode

from flask import Request

REST_PREFIX = "/polarion/rest/v1"

# Polarion's default and maximum page size for collection resources
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 100

# Attributes a part can carry (order as returned by Polarion)
PART_ATTRIBUTE_ORDER = ("id", "type", "content", "level", "external")


def parse_fields(value: Optional[str]) -> Optional[List[str]]:
    """Parse a ``fields[<type>]`` value.

    ``None``/``@all``/``@basic`` -> ``None`` (= every attribute; the mock is
    lenient and treats ``@basic`` like ``@all``). Otherwise the comma separated
    list of attribute names.
    """
    if value is None:
        return None
    value = value.strip()
    if not value or value in ("@all", "@basic"):
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def apply_fields(attributes: Dict[str, Any], fields: Optional[List[str]]) -> Dict[str, Any]:
    """Keep only the requested attributes (sparse fieldsets)."""
    if fields is None:
        return attributes
    return {key: value for key, value in attributes.items() if key in fields}


def parse_pagination(args) -> Tuple[int, int]:
    """Return ``(page_size, page_number)`` from ``page[size]``/``page[number]``."""
    try:
        page_size = int(args.get("page[size]", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        page_size = DEFAULT_PAGE_SIZE
    try:
        page_number = int(args.get("page[number]", 1))
    except (TypeError, ValueError):
        page_number = 1
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    page_number = max(1, page_number)
    return page_size, page_number


def page_url(request: Request, page_number: int) -> str:
    """The request URL with ``page[number]`` replaced, encoded like Polarion.

    Polarion percent-encodes the brackets (``%5B``/``%5D``) and the ``@`` in
    ``@all`` (``%40``); every other query parameter of the request is kept.
    """
    params: List[Tuple[str, str]] = []
    seen_page = False
    for key, values in request.args.to_dict(flat=False).items():
        for value in values:
            if key == "page[number]":
                if not seen_page:
                    params.append((key, str(page_number)))
                    seen_page = True
            else:
                params.append((key, value))
    if not seen_page:
        params.append(("page[number]", str(page_number)))
    return f"{request.base_url}?{urlencode(params, quote_via=quote)}"


def pagination_links(request: Request, page_number: int, page_size: int,
                     total_count: int) -> Dict[str, str]:
    """``self``/``first``/``prev``/``next``/``last`` like Polarion returns them."""
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    links = {
        "self": page_url(request, page_number),   # re-encoded like Polarion does
        "first": page_url(request, 1),
    }
    if page_number > 1:
        links["prev"] = page_url(request, min(page_number - 1, total_pages))
    if page_number < total_pages:
        links["next"] = page_url(request, page_number + 1)
    links["last"] = page_url(request, total_pages)
    return links


def paginate(items: List[Any], page_size: int, page_number: int) -> List[Any]:
    """Slice ``items`` for the requested page."""
    start = (page_number - 1) * page_size
    return items[start:start + page_size]


def split_document_id(document_id: str) -> Tuple[str, str, str]:
    """``project/space/name`` -> tuple (space and name may contain spaces)."""
    project_id, space_id, document_name = document_id.split("/", 2)
    return project_id, space_id, document_name


def document_parts_url(base_url: str, document_id: str) -> str:
    """Absolute URL of a document's parts collection."""
    project_id, space_id, document_name = split_document_id(document_id)
    return (f"{base_url}{REST_PREFIX}/projects/{quote(project_id, safe='')}"
            f"/spaces/{quote(space_id, safe='')}/documents/{quote(document_name, safe='')}/parts")


def workitem_url(base_url: str, workitem_id: str) -> str:
    """Absolute URL of a work item (``project/WI-1``)."""
    project_id, short_id = workitem_id.split("/", 1)
    return (f"{base_url}{REST_PREFIX}/projects/{quote(project_id, safe='')}"
            f"/workitems/{quote(short_id, safe='')}")


def part_attributes(part: Dict[str, Any]) -> Dict[str, Any]:
    """The attributes object of a canonical part (None values omitted)."""
    attributes: Dict[str, Any] = {}
    for key in PART_ATTRIBUTE_ORDER:
        value = part.get(key)
        if key == "content":
            attributes[key] = value or ""
        elif value is not None:
            attributes[key] = value
    return attributes


def render_part(document_id: str, part: Dict[str, Any], base_url: str = "",
                fields: Optional[List[str]] = None,
                with_attributes: bool = True) -> Dict[str, Any]:
    """Render a canonical part as a JSON:API resource object."""
    resource: Dict[str, Any] = {
        "type": "document_parts",
        "id": f"{document_id}/{part['id']}",
    }
    if with_attributes:
        attributes = apply_fields(part_attributes(part), fields)
        if attributes:
            resource["attributes"] = attributes
    workitem_id = part.get("workitem_id")
    if workitem_id:
        resource["relationships"] = {
            "workItem": {
                "data": {"type": "workitems", "id": workitem_id},
                "links": {"self": f"{document_parts_url(base_url, document_id)}/"
                                  f"{quote(part['id'], safe='')}/relationships/workItem"},
            }
        }
    resource["links"] = {
        "self": f"{document_parts_url(base_url, document_id)}/{quote(part['id'], safe='')}"
    }
    return resource


def absolutize_links(resource: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """Prefix relative ``links`` (``/polarion/...``) with the server base URL.

    Works on the resource's own links and on the links of its relationships.
    Polarion always returns absolute URLs.
    """
    def _fix(links: Any) -> None:
        if isinstance(links, dict):
            for key, value in list(links.items()):
                if isinstance(value, str) and value.startswith("/"):
                    links[key] = f"{base_url}{value}"

    _fix(resource.get("links"))
    for relationship in (resource.get("relationships") or {}).values():
        if isinstance(relationship, dict):
            _fix(relationship.get("links"))
    return resource


def base_url_of(request: Request) -> str:
    """Scheme + host of the request without trailing slash."""
    return request.host_url.rstrip("/")
