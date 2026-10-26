"""Location CRUD: REST endpoints + HTML GUI."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.codes import format_location_code
from app.db import get_session
from app.models import Location, Placement
from app.templates import templates

router = APIRouter()


class LocationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_code: Optional[str] = None


class LocationUpdate(BaseModel):
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


def _would_create_cycle(session: Session, code: str, new_parent: str) -> bool:
    """True if setting new_parent as parent of `code` creates a cycle."""
    seen = {code}
    cursor: Optional[str] = new_parent
    while cursor:
        if cursor in seen:
            return True
        seen.add(cursor)
        parent = session.get(Location, cursor)
        cursor = parent.parent_code if parent else None
    return False


def update_location(session: Session, code: str, data: LocationUpdate) -> Location:
    loc = session.get(Location, code)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")

    new_parent = data.parent_code or None
    if new_parent:
        if new_parent == code:
            raise HTTPException(status_code=400, detail="location cannot be its own parent")
        parent = session.get(Location, new_parent)
        if parent is None:
            raise HTTPException(status_code=400, detail="parent_code not found")
        if _would_create_cycle(session, code, new_parent):
            raise HTTPException(status_code=400, detail="parent_code would create a cycle")

    loc.name = data.name
    loc.description = data.description
    loc.parent_code = new_parent
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc


def delete_location(session: Session, code: str) -> None:
    loc = session.get(Location, code)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")

    children = session.exec(
        select(Location).where(Location.parent_code == code)
    ).all()
    if children:
        raise HTTPException(
            status_code=409,
            detail="location has sub-locations; delete or reassign them first",
        )

    active_placements = session.exec(
        select(Placement).where(
            Placement.location_code == code,
            Placement.active == True,  # noqa: E712
        )
    ).all()
    if active_placements:
        raise HTTPException(
            status_code=409,
            detail="location still holds items; remove them first",
        )

    # drop inactive placement history referencing this location to avoid FK orphans
    stale = session.exec(
        select(Placement).where(Placement.location_code == code)
    ).all()
    for p in stale:
        session.delete(p)
    session.delete(loc)
    session.commit()


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


@router.put("/api/locations/{code}", response_model=LocationRead)
def api_update_location(
    code: str, data: LocationUpdate, session: Session = Depends(get_session)
) -> Location:
    return update_location(session, code, data)


@router.delete("/api/locations/{code}", status_code=204)
def api_delete_location(code: str, session: Session = Depends(get_session)):
    delete_location(session, code)
    return Response(status_code=204)


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
    request: Request,
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
    base = request.headers.get("X-Ingress-Path", "")
    return RedirectResponse(url=f"{base}/locations", status_code=303)


@router.get("/locations/{code}/edit", response_class=HTMLResponse)
def html_edit_location_form(
    code: str, request: Request, session: Session = Depends(get_session)
):
    loc = session.get(Location, code)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")
    # possible parents: every location except this one (cycle check happens on save)
    others = session.exec(
        select(Location).where(Location.code != code).order_by(Location.code)
    ).all()
    return templates.TemplateResponse(
        request,
        "location_edit.html",
        {"loc": loc, "locations": others},
    )


@router.post("/locations/{code}/edit")
def html_update_location(
    code: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    parent_code: str = Form(""),
    session: Session = Depends(get_session),
):
    update_location(
        session,
        code,
        LocationUpdate(
            name=name,
            description=description or None,
            parent_code=parent_code or None,
        ),
    )
    base = request.headers.get("X-Ingress-Path", "")
    return RedirectResponse(url=f"{base}/locations", status_code=303)


@router.post("/locations/{code}/delete")
def html_delete_location(
    code: str, request: Request, session: Session = Depends(get_session)
):
    base = request.headers.get("X-Ingress-Path", "")
    try:
        delete_location(session, code)
    except HTTPException as exc:
        locations = session.exec(select(Location).order_by(Location.code)).all()
        return templates.TemplateResponse(
            request,
            "locations.html",
            {"locations": locations, "error": exc.detail},
            status_code=exc.status_code,
        )
    return RedirectResponse(url=f"{base}/locations", status_code=303)
