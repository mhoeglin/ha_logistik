"""Stateful scan workflow engine.

Handles a sequence of scanned codes for the STORE (Einlagern) workflow:

    CMD:STORE  -> enter STORE mode, clears current location
    LOC:xxxxxx -> set the current target location
    ITM:xxxxxx -> assign the item to the current location (needs a location first)

Only STORE is functional in this iteration; other commands
(REMOVE/MOVE/LEND/RETURN) are recognised and acknowledged as "not yet
implemented" so the scheme is future-proof.

Session state is kept server-side in a small in-memory dict keyed by an
opaque session id supplied by the client (cookie/body). The engine itself is
pure enough to be unit-tested by driving `handle_scan` directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from sqlmodel import Session, select

from app.codes import CodeKind, parse_code
from app.models import Action, Item, Location, MovementLog, Placement


@dataclass
class ScanState:
    mode: str | None = None  # "STORE" (others later)
    location_code: str | None = None
    location_name: str | None = None


@dataclass
class ScanResult:
    ok: bool
    message: str
    kind: str  # CodeKind value or "error"
    mode: str | None = None
    location_code: str | None = None
    location_name: str | None = None
    item_code: str | None = None
    item_title: str | None = None
    warnings: list[str] = field(default_factory=list)


IMPLEMENTED_COMMANDS = {"STORE"}
KNOWN_COMMANDS = {"STORE", "REMOVE", "MOVE", "LEND", "RETURN"}


class ScanSessionStore:
    """Thread-safe in-memory store of per-session ScanState."""

    def __init__(self) -> None:
        self._states: dict[str, ScanState] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> ScanState:
        with self._lock:
            return self._states.setdefault(session_id, ScanState())

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._states[session_id] = ScanState()


def _result_from_state(state: ScanState, **kwargs) -> ScanResult:
    kwargs.setdefault("mode", state.mode)
    kwargs.setdefault("location_code", state.location_code)
    kwargs.setdefault("location_name", state.location_name)
    return ScanResult(**kwargs)


def _store_item(session: Session, item_code: str, location_code: str) -> None:
    """Deactivate any active placement of the item and add a new active one."""
    active = session.exec(
        select(Placement).where(
            Placement.item_code == item_code, Placement.active == True  # noqa: E712
        )
    ).all()
    from_location = active[0].location_code if active else None
    for p in active:
        p.active = False
        session.add(p)
    session.add(Placement(item_code=item_code, location_code=location_code, active=True))
    session.add(
        MovementLog(
            item_code=item_code,
            from_location=from_location,
            to_location=location_code,
            action=Action.STORE,
        )
    )
    session.commit()


def handle_scan(session: Session, state: ScanState, raw: str) -> ScanResult:
    """Process one scanned code against the given state; mutates state."""
    parsed = parse_code(raw)

    if parsed.kind == CodeKind.COMMAND:
        cmd = parsed.value
        if cmd not in KNOWN_COMMANDS:
            return _result_from_state(
                state, ok=False, kind="command",
                message=f"Unbekanntes Kommando: {cmd}",
            )
        if cmd not in IMPLEMENTED_COMMANDS:
            return _result_from_state(
                state, ok=False, kind="command",
                message=f"Kommando '{cmd}' ist noch nicht implementiert.",
            )
        state.mode = cmd
        state.location_code = None
        state.location_name = None
        return _result_from_state(
            state, ok=True, kind="command",
            message="Modus EINLAGERN aktiv. Bitte Lagerort scannen.",
        )

    if parsed.kind == CodeKind.LOCATION:
        loc = session.get(Location, parsed.raw)
        if loc is None:
            return _result_from_state(
                state, ok=False, kind="location",
                message=f"Lagerort {parsed.raw} nicht gefunden.",
            )
        if state.mode is None:
            # Scanning a location without a command: default to informing.
            return _result_from_state(
                state, ok=False, kind="location",
                message="Kein Modus aktiv. Bitte zuerst ein Kommando scannen (z.B. CMD:STORE).",
            )
        state.location_code = loc.code
        state.location_name = loc.name
        return _result_from_state(
            state, ok=True, kind="location",
            message=f"Lagerort gesetzt: {loc.name}. Jetzt Artikel scannen.",
        )

    if parsed.kind == CodeKind.ITEM:
        item = session.get(Item, parsed.raw)
        if item is None:
            return _result_from_state(
                state, ok=False, kind="item",
                message=f"Artikel {parsed.raw} nicht gefunden.",
            )
        if state.mode != "STORE":
            return _result_from_state(
                state, ok=False, kind="item",
                message="Kein EINLAGERN-Modus aktiv. Bitte CMD:STORE scannen.",
            )
        if state.location_code is None:
            return _result_from_state(
                state, ok=False, kind="item",
                message="Kein Lagerort gesetzt. Bitte zuerst einen Lagerort scannen.",
            )
        _store_item(session, item.code, state.location_code)
        return _result_from_state(
            state, ok=True, kind="item",
            item_code=item.code, item_title=item.title,
            message=f"{item.title} → {state.location_name}",
        )

    return _result_from_state(
        state, ok=False, kind="unknown",
        message=f"Unbekannter Code: {parsed.raw}",
    )
