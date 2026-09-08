"""Scan endpoints: POST /scan drives the stateful workflow."""
from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.scan import ScanSessionStore, handle_scan
from app.templates import templates

router = APIRouter()

_store = ScanSessionStore()

SESSION_COOKIE = "scan_session"


class ScanRequest(BaseModel):
    code: str


def _ensure_session_id(session_id: str | None, response: Response) -> str:
    if not session_id:
        session_id = uuid.uuid4().hex
        response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax")
    return session_id


@router.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request):
    return templates.TemplateResponse(request, "scan.html", {})


@router.post("/scan")
def scan(
    payload: ScanRequest,
    response: Response,
    scan_session: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> dict:
    session_id = _ensure_session_id(scan_session, response)
    state = _store.get(session_id)
    result = handle_scan(session, state, payload.code)
    return asdict(result)


@router.post("/scan/reset")
def scan_reset(
    response: Response,
    scan_session: str | None = Cookie(default=None),
) -> dict:
    session_id = _ensure_session_id(scan_session, response)
    _store.reset(session_id)
    return {"ok": True, "message": "Sitzung zurückgesetzt."}
