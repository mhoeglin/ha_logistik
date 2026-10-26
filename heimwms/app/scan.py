"""Stateful scan workflow engine.

Scan a COMMAND, then (for location-based actions) a LOCATION, then ITEMs.

Actions and their semantics:
- STORE   : place item at the current location. If the location is a *sink*
            (e.g. Mülleimer) the item is disposed instead. Status -> stored
            (or disposed). Requires a location.
- MOVE    : same as STORE but logged as MOVE (relocation). Requires a location.
- REMOVE  : take item out; keeps the item, deactivates its active placement.
            Status -> removed. Item only (no location needed).
- LEND    : lend item out; deactivates placement. Status -> lent. Item only.
- RETURN  : return a lent/removed item to a location. Requires a location.
            Status -> stored.

A location's `direction`:
- normal : store & remove allowed.
- sink   : incoming only; STORE/MOVE here => item disposed.
- source : outgoing only; cannot STORE/MOVE into it (error).

The engine mutates a ScanState (mode + current location) and returns a
ScanResult. It is pure enough to be unit-tested by calling handle_scan().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from sqlmodel import Session, select

from app.codes import CodeKind, parse_code
from app.models import (
    Action,
    Item,
    ItemStatus,
    Location,
    LocationDirection,
    MovementLog,
    Placement,
)

# Actions that require a location to be scanned before items.
LOCATION_ACTIONS = {"STORE", "MOVE", "RETURN"}
# Actions that operate on an item directly (no location needed).
ITEM_ONLY_ACTIONS = {"REMOVE", "LEND"}
KNOWN_COMMANDS = LOCATION_ACTIONS | ITEM_ONLY_ACTIONS

_MODE_LABELS = {
    "STORE": "EINLAGERN",
    "MOVE": "UMZUG",
    "RETURN": "ZURÜCKGEBEN",
    "REMOVE": "AUSLAGERN",
    "LEND": "AUSLEIHEN",
}


@dataclass
class ScanState:
    mode: str | None = None
    location_code: str | None = None
    location_name: str | None = None


@dataclass
class ScanResult:
    ok: bool
    message: str
    kind: str  # "command" | "location" | "item" | "unknown" | "error"
    mode: str | None = None
    location_code: str | None = None
    location_name: str | None = None
    item_code: str | None = None
    item_title: str | None = None
    action: str | None = None
    item_status: str | None = None
    warnings: list[str] = field(default_factory=list)


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


def _active_placement(session: Session, item_code: str) -> Placement | None:
    return session.exec(
        select(Placement).where(
            Placement.item_code == item_code,
            Placement.active == True,  # noqa: E712
        )
    ).first()


def _deactivate_placements(session: Session, item_code: str) -> str | None:
    """Deactivate all active placements; return the previous location code."""
    active = session.exec(
        select(Placement).where(
            Placement.item_code == item_code,
            Placement.active == True,  # noqa: E712
        )
    ).all()
    prev = active[0].location_code if active else None
    for p in active:
        p.active = False
        session.add(p)
    return prev


def _place_item(
    session: Session,
    item: Item,
    location: Location,
    action: Action,
) -> ScanResult | None:
    """Place item at location, honouring sink/source direction. Commits."""
    if location.direction == LocationDirection.source:
        return ScanResult(
            ok=False, kind="item", item_code=item.code, item_title=item.title,
            message=f"{location.name} ist eine Quelle (nur Ausgang) – Einlagern nicht möglich.",
        )

    prev = _deactivate_placements(session, item.code)

    if location.direction == LocationDirection.sink:
        # Storing into a sink disposes the item; no active placement.
        item.status = ItemStatus.disposed
        item.lent_to = None
        session.add(item)
        session.add(MovementLog(
            item_code=item.code, from_location=prev,
            to_location=location.code, action=Action.DISPOSE,
        ))
        session.commit()
        return ScanResult(
            ok=True, kind="item", item_code=item.code, item_title=item.title,
            action=Action.DISPOSE.value, item_status=item.status.value,
            message=f"{item.title} → entsorgt ({location.name})",
        )

    # Normal placement.
    session.add(Placement(item_code=item.code, location_code=location.code, active=True))
    item.status = ItemStatus.stored
    item.lent_to = None
    session.add(item)
    session.add(MovementLog(
        item_code=item.code, from_location=prev,
        to_location=location.code, action=action,
    ))
    session.commit()
    return None  # caller builds the success result with state context


def handle_scan(session: Session, state: ScanState, raw: str) -> ScanResult:
    """Process one scanned code against the given state; mutates state."""
    parsed = parse_code(raw)

    if parsed.kind == CodeKind.COMMAND:
        return _handle_command(state, parsed.value)
    if parsed.kind == CodeKind.LOCATION:
        return _handle_location(session, state, parsed.raw)
    if parsed.kind == CodeKind.ITEM:
        return _handle_item(session, state, parsed.raw)

    return _result_from_state(
        state, ok=False, kind="unknown",
        message=f"Unbekannter Code: {parsed.raw}",
    )


def _handle_command(state: ScanState, cmd: str) -> ScanResult:
    if cmd not in KNOWN_COMMANDS:
        return _result_from_state(
            state, ok=False, kind="command",
            message=f"Unbekanntes Kommando: {cmd}",
        )
    state.mode = cmd
    state.location_code = None
    state.location_name = None
    label = _MODE_LABELS.get(cmd, cmd)
    if cmd in LOCATION_ACTIONS:
        hint = "Bitte Lagerort scannen."
    else:
        hint = "Bitte Artikel scannen."
    return _result_from_state(
        state, ok=True, kind="command",
        message=f"Modus {label} aktiv. {hint}",
    )


def _handle_location(session: Session, state: ScanState, code: str) -> ScanResult:
    loc = session.get(Location, code)
    if loc is None:
        return _result_from_state(
            state, ok=False, kind="location",
            message=f"Lagerort {code} nicht gefunden.",
        )
    if state.mode is None:
        return _result_from_state(
            state, ok=False, kind="location",
            message="Kein Modus aktiv. Bitte zuerst ein Kommando scannen (z.B. CMD:STORE).",
        )
    if state.mode not in LOCATION_ACTIONS:
        return _result_from_state(
            state, ok=False, kind="location",
            message=f"Im Modus {_MODE_LABELS.get(state.mode, state.mode)} wird kein Lagerort benötigt. Bitte Artikel scannen.",
        )
    state.location_code = loc.code
    state.location_name = loc.name
    return _result_from_state(
        state, ok=True, kind="location",
        message=f"Lagerort gesetzt: {loc.name}. Jetzt Artikel scannen.",
    )


def _handle_item(session: Session, state: ScanState, code: str) -> ScanResult:
    item = session.get(Item, code)
    if item is None:
        return _result_from_state(
            state, ok=False, kind="item",
            message=f"Artikel {code} nicht gefunden.",
        )
    if state.mode is None:
        return _result_from_state(
            state, ok=False, kind="item",
            message="Kein Modus aktiv. Bitte zuerst ein Kommando scannen.",
        )

    mode = state.mode

    # Location-based actions: STORE / MOVE / RETURN
    if mode in LOCATION_ACTIONS:
        if state.location_code is None:
            return _result_from_state(
                state, ok=False, kind="item",
                message="Kein Lagerort gesetzt. Bitte zuerst einen Lagerort scannen.",
            )
        location = session.get(Location, state.location_code)
        action = {"STORE": Action.STORE, "MOVE": Action.MOVE, "RETURN": Action.RETURN}[mode]
        placed = _place_item(session, item, location, action)
        if placed is not None:
            return placed  # error (e.g. source) or dispose result
        return _result_from_state(
            state, ok=True, kind="item",
            item_code=item.code, item_title=item.title,
            action=action.value, item_status=ItemStatus.stored.value,
            message=f"{item.title} → {state.location_name}",
        )

    # Item-only actions: REMOVE / LEND
    prev = _deactivate_placements(session, item.code)
    if mode == "REMOVE":
        item.status = ItemStatus.removed
        item.lent_to = None
        act = Action.REMOVE
        msg = f"{item.title} ausgelagert"
    else:  # LEND
        item.status = ItemStatus.lent
        act = Action.LEND
        msg = f"{item.title} ausgeliehen"
    session.add(item)
    session.add(MovementLog(
        item_code=item.code, from_location=prev, to_location=None, action=act,
    ))
    session.commit()
    return _result_from_state(
        state, ok=True, kind="item",
        item_code=item.code, item_title=item.title,
        action=act.value, item_status=item.status.value,
        message=msg,
    )
