"""Scan endpoints driving the global scan station.

- GET  /scan        -> the live scan page
- POST /scan        -> process a scanned code (JSON {code})
- GET  /scan/state  -> current station snapshot (for live polling)
- POST /scan/reset  -> reset the station
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.station import station
from app.templates import templates

router = APIRouter()


class ScanRequest(BaseModel):
    code: str


@router.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request):
    return templates.TemplateResponse(request, "scan.html", {})


@router.post("/scan")
def scan(payload: ScanRequest, session: Session = Depends(get_session)) -> dict:
    result = station.process(session, payload.code)
    return asdict(result)


@router.get("/scan/state")
def scan_state() -> dict:
    return station.snapshot()


@router.post("/scan/reset")
def scan_reset() -> dict:
    station.reset()
    return {"ok": True, "message": "Station zurückgesetzt."}
