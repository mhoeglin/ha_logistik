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
    karton = "karton"
    kiste = "kiste"
    werkzeug = "werkzeug"
    lebensmittel = "lebensmittel"
    material = "material"

    @property
    def label(self) -> str:
        return {
            "karton": "Karton",
            "kiste": "Kiste",
            "werkzeug": "Werkzeug",
            "lebensmittel": "Lebensmittel",
            "material": "Material",
        }[self.value]

    @classmethod
    def _missing_(cls, value):
        # Backwards compatibility: map legacy English values to the new ones.
        legacy = {
            "box": cls.karton,
            "food": cls.lebensmittel,
            "tool": cls.werkzeug,
            "other": cls.material,
        }
        if isinstance(value, str):
            v = value.strip().lower()
            if v in legacy:
                return legacy[v]
            # also accept German labels / capitalised input
            for member in cls:
                if v == member.value or v == member.label.lower():
                    return member
        return None


class LocationDirection(str, Enum):
    """Whether a location accepts items in, out, or both.

    - normal: bidirectional (store and remove).
    - sink: incoming only; storing here disposes the item (e.g. Mülleimer).
    - source: outgoing only; items originate here (e.g. Neukauf-Eingang).
    """

    normal = "normal"
    sink = "sink"
    source = "source"


class ItemStatus(str, Enum):
    stored = "stored"        # currently placed at an active location
    removed = "removed"      # taken out, still exists, no active location
    lent = "lent"            # lent out (optionally to someone)
    disposed = "disposed"    # discarded / gone


class Action(str, Enum):
    STORE = "STORE"
    REMOVE = "REMOVE"
    MOVE = "MOVE"
    LEND = "LEND"
    RETURN = "RETURN"
    DISPOSE = "DISPOSE"      # store into a sink location
    ACQUIRE = "ACQUIRE"      # first placement / from a source


class Location(SQLModel, table=True):
    __tablename__ = "location"

    code: str = Field(primary_key=True, description="e.g. LOC:000123")
    name: str
    description: Optional[str] = None
    direction: LocationDirection = Field(default=LocationDirection.normal)
    parent_code: Optional[str] = Field(
        default=None, foreign_key="location.code", index=True
    )
    created_at: datetime = Field(default_factory=utcnow)


class Item(SQLModel, table=True):
    __tablename__ = "item"

    code: str = Field(primary_key=True, description="e.g. ITM:000123")
    title: str
    description: Optional[str] = None
    type: ItemType = Field(default=ItemType.karton)
    status: ItemStatus = Field(default=ItemStatus.stored, index=True)
    lent_to: Optional[str] = None
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
