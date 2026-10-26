"""Global scan-station state.

A home warehouse typically has one logical "scan station" that any input
method drives: the browser HID page, the HTTP push endpoint, and (later)
MQTT. They all share a single server-side ScanState so the workflow context
(current mode + location) is consistent regardless of who scanned.

The last processed result is also kept so the live UI can poll it.
"""
from __future__ import annotations

from dataclasses import asdict
from threading import Lock

from sqlmodel import Session

from app.scan import ScanResult, ScanState, handle_scan

DEFAULT_STATION = "default"


class Station:
    def __init__(self) -> None:
        self._states: dict[str, ScanState] = {}
        self._last: dict[str, dict] = {}
        self._lock = Lock()

    def state(self, station_id: str = DEFAULT_STATION) -> ScanState:
        with self._lock:
            return self._states.setdefault(station_id, ScanState())

    def reset(self, station_id: str = DEFAULT_STATION) -> None:
        with self._lock:
            self._states[station_id] = ScanState()
            self._last[station_id] = {
                "ok": True,
                "kind": "reset",
                "message": "Station zurückgesetzt.",
                "mode": None,
                "location_code": None,
                "location_name": None,
                "item_code": None,
                "item_title": None,
                "action": None,
                "item_status": None,
                "warnings": [],
            }

    def process(
        self, session: Session, code: str, station_id: str = DEFAULT_STATION
    ) -> ScanResult:
        state = self.state(station_id)
        result = handle_scan(session, state, code)
        with self._lock:
            self._last[station_id] = asdict(result)
        return result

    def snapshot(self, station_id: str = DEFAULT_STATION) -> dict:
        """Current station view for the live UI (state + last result)."""
        state = self.state(station_id)
        with self._lock:
            last = self._last.get(station_id)
        return {
            "mode": state.mode,
            "location_code": state.location_code,
            "location_name": state.location_name,
            "last": last,
        }


# Module-level singleton shared across all routers/inputs.
station = Station()
