"""Location CRUD: REST endpoints + HTML GUI."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.codes import format_location_code
from app.db import get_session
from app.models import Location
from app.templates import templates

router = APIRouter()


class LocationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_code: Optional[str] = None


class LocationRead(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    parent_code: Optional[str] = None


def _next_location_code(session: Session) -> str:
    """Generate the next LOC code by scanning existing numeric suffixes."""
    codes = session.exec(select(Location.code)).all()
    max_num = 0
    for c in codes:
        try:
            n = int(c.split(":", 1)[1])
            max_num = max(max_num, n)
        except (IndexError, ValueError):
            continue
    return format_location_code(max_num + 1)


def create_location(session: Session, data: LocationCreate) -> Location:
    if data.parent_code:
        parent = session.get(Location, data.parent_code)
        if parent is None:
            raise HTTPException(status_code=400, detail="parent_code not found")
    loc = Location(
        code=_next_location_code(session),
        name=data.name,
        description=data.description,
        parent_code=data.parent_code or None,
    )
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc


# ---- REST API ----

@router.post("/api/locations", response_model=LocationRead, status_code=201)
def api_create_location(
    data: LocationCreate, session: Session = Depends(get_session)
) -> Location:
    return create_location(session, data)


@router.get("/api/locations", response_model=list[LocationRead])
def api_list_locations(session: Session = Depends(get_session)) -> list[Location]:
    return session.exec(select(Location).order_by(Location.code)).all()


@router.get("/api/locations/{code}", response_model=LocationRead)
def api_get_location(code: str, session: Session = Depends(get_session)) -> Location:
    loc = session.get(Location, code)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")
    return loc


# ---- HTML GUI ----

@router.get("/locations", response_class=HTMLResponse)
def html_list_locations(request: Request, session: Session = Depends(get_session)):
    locations = session.exec(select(Location).order_by(Location.code)).all()
    return templates.TemplateResponse(
        request,
        "locations.html",
        {"locations": locations},
    )


@router.post("/locations")
def html_create_location(
    name: str = Form(...),
    description: str = Form(""),
    parent_code: str = Form(""),
    session: Session = Depends(get_session),
):
    create_location(
        session,
        LocationCreate(
            name=name,
            description=description or None,
            parent_code=parent_code or None,
        ),
    )
    return RedirectResponse(url="/locations", status_code=303)
