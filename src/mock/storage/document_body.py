"""
The text of a LiveDoc and its parts are one thing.

Polarion keeps a single text per LiveDoc, the ``homePageContent`` attribute.
``GET .../documents/{name}/parts`` is a view of that text: one part per
top-level block, in text order. A work item sits in the text as a macro
element, a heading as ``<hN id="polarion_wiki macro name=module-workitem;
params=id=PROJ-1">``, any other work item as ``<div id="...">``; every other
block carries its own id (``polarion_7``, ``polarion_wiki macro name=toc``,
``polarion_editor_html_block1`` ...), which names its part.

The mock stores the parts and renders the text from them (``render_body``).
A written text is split back into parts (``split_body``), so a reader of the
text and a reader of the parts always see the same document.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# Separator between the blocks of a rendered text
BLOCK_SEPARATOR = "\n"

_TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)\b([^>]*?)(/?)>|<!--.*?-->", re.S)
_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_ID_ATTR = re.compile(r'\bid\s*=\s*"([^"]*)"')
_WORKITEM_MACRO = "polarion_wiki macro name=module-workitem;params="
_MACRO = re.compile(r"^polarion_wiki macro name=([A-Za-z_]+)[^;]*;params=(.*)$")
_UID_PARAM = re.compile(r"(?:^|\|)uid=(\d+)(?:\||$)")
_HTML_BLOCK = re.compile(r"^polarion_editor_html_block(\d+)$")
_HEADING_TAG = re.compile(r"^h[1-6]$", re.I)

# Part type of a ``name=...;params=uid=N`` macro, as Polarion lists it
_UID_MACRO_TYPES = {"page_break": "pagebreak"}


class DocumentBodyError(ValueError):
    """The text cannot be split into parts."""


def split_blocks(html: str) -> List[str]:
    """The top-level blocks of ``html`` in order, each exactly as written.

    Whitespace between blocks is dropped; text outside any element is a block
    of its own; an element left open runs to the end of the text.
    """
    blocks: List[str] = []
    depth = 0
    start: Optional[int] = None
    position = 0
    for match in _TAG.finditer(html):
        if match.group(2) is None:  # comment
            continue
        closing, self_closing = match.group(1), match.group(4)
        name = match.group(2).lower()
        if depth == 0:
            text = html[position : match.start()]
            if text.strip():
                blocks.append(text.strip())
            position = match.start()
        if closing:
            if depth == 0:
                position = match.end()
                continue
            depth -= 1
            if depth == 0:
                blocks.append(html[start : match.end()])
                start, position = None, match.end()
        elif self_closing or name in _VOID:
            if depth == 0:
                blocks.append(html[match.start() : match.end()])
                position = match.end()
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    if start is not None:
        blocks.append(html[start:])
    elif html[position:].strip():
        blocks.append(html[position:].strip())
    return blocks


def _workitem_params(element_id: str) -> Dict[str, str]:
    """``id=PROJ-1|layout=2|project=Other`` -> ``{"id": ..., "layout": ...}``."""
    params: Dict[str, str] = {}
    for item in element_id[len(_WORKITEM_MACRO) :].split("|"):
        key, _, value = item.partition("=")
        params[key.strip()] = value.strip()
    return params


def describe_block(block: str, project_id: str) -> Dict[str, Any]:
    """The part a block stands for: id, type, referenced work item, content.

    A block without an id (plain text, or an element Polarion has not named)
    gets ``id`` None.
    """
    tag = _TAG.match(block)
    element_id = None
    if tag and tag.group(2) and not tag.group(1):
        found = _ID_ATTR.search(tag.group(3))
        element_id = found.group(1) if found else None
    part: Dict[str, Any] = {
        "id": None,
        "type": "normal",
        "content": block,
        "workitem_id": None,
        "external": None,
    }
    if not element_id:
        return part
    if element_id.startswith(_WORKITEM_MACRO):
        params = _workitem_params(element_id)
        short_id = params.get("id")
        if not short_id:
            raise DocumentBodyError(f"work item macro without an id: {block[:120]}")
        part_type = "heading" if _HEADING_TAG.match(tag.group(2)) else "workitem"
        other_project = params.get("project")
        part.update(
            id=f"{part_type}_{short_id}",
            type=part_type,
            workitem_id=f"{other_project or project_id}/{short_id}",
        )
        if other_project and other_project != project_id:
            part["external"] = True
        return part
    if element_id == "polarion_wiki macro name=toc":
        part.update(id="toc", type="toc")
        return part
    macro = _MACRO.match(element_id)
    uid = _UID_PARAM.search(macro.group(2)) if macro else None
    if macro and uid:
        part_type = _UID_MACRO_TYPES.get(macro.group(1), macro.group(1))
        part.update(id=f"{part_type}_{uid.group(1)}", type=part_type)
        return part
    html_block = _HTML_BLOCK.match(element_id)
    if html_block:
        part.update(id=f"wikiblock_{html_block.group(1)}", type="wikiblock")
        return part
    part["id"] = element_id
    return part


def split_body(html: str, project_id: str) -> List[Dict[str, Any]]:
    """The parts of a document text, in order."""
    parts = [describe_block(block, project_id) for block in split_blocks(html or "")]
    seen: Dict[str, int] = {}
    for part in parts:
        if part["id"] is None:
            continue
        if part["id"] in seen:
            raise DocumentBodyError(
                f"part {part['id']} appears twice in the document text"
            )
        seen[part["id"]] = 1
    return parts


def render_body(contents: List[str]) -> str:
    """The document text made of the parts' contents."""
    return BLOCK_SEPARATOR.join(contents)


def unnamed_blocks(parts: List[Dict[str, Any]]) -> List[Tuple[int, str]]:
    """``(position, content)`` of every part without an id (1-based)."""
    return [
        (index, part["content"])
        for index, part in enumerate(parts, start=1)
        if part.get("id") is None
    ]
