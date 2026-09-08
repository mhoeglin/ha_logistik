"""Barcode/QR code scheme helpers.

Code scheme (payload encoded into QR and 1D barcodes):
- Location: "LOC:000123"
- Item:     "ITM:000123"
- Command:  "CMD:STORE" (also REMOVE/MOVE/LEND/RETURN)

Numeric IDs are zero-padded to 6 digits. Code128 can encode the full
"LOC:000123" string directly, keeping QR and 1D payloads identical.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

LOC_PREFIX = "LOC:"
ITM_PREFIX = "ITM:"
CMD_PREFIX = "CMD:"

_NUM_RE = re.compile(r"^\d{1,}$")


class CodeKind(str, Enum):
    LOCATION = "location"
    ITEM = "item"
    COMMAND = "command"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ParsedCode:
    kind: CodeKind
    raw: str
    value: str  # payload after the prefix (e.g. "000123" or "STORE")


def format_location_code(num: int) -> str:
    return f"{LOC_PREFIX}{num:06d}"


def format_item_code(num: int) -> str:
    return f"{ITM_PREFIX}{num:06d}"


def format_command_code(action: str) -> str:
    return f"{CMD_PREFIX}{action.upper()}"


def parse_code(raw: str) -> ParsedCode:
    """Classify a scanned/typed string into a ParsedCode."""
    s = (raw or "").strip()
    if s.startswith(LOC_PREFIX):
        return ParsedCode(CodeKind.LOCATION, s, s[len(LOC_PREFIX):])
    if s.startswith(ITM_PREFIX):
        return ParsedCode(CodeKind.ITEM, s, s[len(ITM_PREFIX):])
    if s.startswith(CMD_PREFIX):
        return ParsedCode(CodeKind.COMMAND, s, s[len(CMD_PREFIX):].upper())
    return ParsedCode(CodeKind.UNKNOWN, s, s)
