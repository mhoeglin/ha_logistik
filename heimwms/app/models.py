"""SQLModel data models for Heim-WMS.

Core entities:
- Location: a storage place (code "LOC:xxxx"), optionally hierarchical.
- Item: a box / article / food / tool (code "ITM:xxxx").
- Placement: links an Item to a Location; `active` marks the current one.
- ItemContent: optional free-text content lines for an Item.
- Photo: optional photo file references for an Item.
- MovementLog: append-only audit trail of actions.

The scan-command actions are modelled as a string enum so future actions
(REMOVE/MOVE/LEND/RETURN) are already representable even though only STORE
is wired up in this iteration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ItemType(str, Enum):
    box = "box"
    food = "food"
    tool = "tool"
    other = "other"


class Action(str, Enum):
    STORE = "STORE"
    REMOVE = "REMOVE"
    MOVE = "MOVE"
    LEND = "LEND"
    RETURN = "RETURN"


class Location(SQLModel, table=True):
    __tablename__ = "location"

    code: str = Field(primary_key=True, description="e.g. LOC:000123")
    name: str
    description: Optional[str] = None
    parent_code: Optional[str] = Field(
        default=None, foreign_key="location.code", index=True
    )
    created_at: datetime = Field(default_factory=utcnow)


class Item(SQLModel, table=True):
    __tablename__ = "item"

    code: str = Field(primary_key=True, description="e.g. ITM:000123")
    title: str
    description: Optional[str] = None
    type: ItemType = Field(default=ItemType.box)
    created_at: datetime = Field(default_factory=utcnow)


class Placement(SQLModel, table=True):
    __tablename__ = "placement"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_code: str = Field(foreign_key="item.code", index=True)
    location_code: str = Field(foreign_key="location.code", index=True)
    placed_at: datetime = Field(default_factory=utcnow)
    active: bool = Field(default=True, index=True)


class ItemContent(SQLModel, table=True):
    __tablename__ = "item_content"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_code: str = Field(foreign_key="item.code", index=True)
    text: str
    quantity: int = Field(default=1)


class Photo(SQLModel, table=True):
    __tablename__ = "photo"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_code: str = Field(foreign_key="item.code", index=True)
    path: str
    created_at: datetime = Field(default_factory=utcnow)


class MovementLog(SQLModel, table=True):
    __tablename__ = "movement_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_code: str = Field(index=True)
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    action: Action = Field(default=Action.STORE)
    ts: datetime = Field(default_factory=utcnow)
