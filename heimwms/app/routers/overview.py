"""Overview & query views: what is where, item location + history, search."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, or_, select

from app.db import get_session
from app.models import Item, Location, MovementLog, Placement
from app.templates import templates

router = APIRouter()


def items_in_location(session: Session, location_code: str) -> list[Item]:
    stmt = (
        select(Item)
        .join(Placement, Placement.item_code == Item.code)
        .where(
            Placement.location_code == location_code,
            Placement.active == True,  # noqa: E712
        )
        .order_by(Item.code)
    )
    return session.exec(stmt).all()


def current_location(session: Session, item_code: str) -> Location | None:
    placement = session.exec(
        select(Placement).where(
            Placement.item_code == item_code,
            Placement.active == True,  # noqa: E712
        )
    ).first()
    if placement is None:
        return None
    return session.get(Location, placement.location_code)


def item_history(session: Session, item_code: str) -> list[MovementLog]:
    return session.exec(
        select(MovementLog)
        .where(MovementLog.item_code == item_code)
        .order_by(MovementLog.ts.desc())
    ).all()


def search_items(session: Session, q: str) -> list[Item]:
    like = f"%{q}%"
    return session.exec(
        select(Item).where(or_(Item.code.like(like), Item.title.like(like)))
    ).all()


# ---- API ----

@router.get("/api/locations/{code}/items")
def api_items_in_location(code: str, session: Session = Depends(get_session)):
    return [{"code": i.code, "title": i.title} for i in items_in_location(session, code)]


@router.get("/api/items/{code}/location")
def api_item_location(code: str, session: Session = Depends(get_session)):
    loc = current_location(session, code)
    return {"location_code": loc.code if loc else None,
            "location_name": loc.name if loc else None}


@router.get("/api/items/{code}/history")
def api_item_history(code: str, session: Session = Depends(get_session)):
    return [
        {
            "action": log.action.value if hasattr(log.action, "value") else log.action,
            "from_location": log.from_location,
            "to_location": log.to_location,
            "ts": log.ts.isoformat(),
        }
        for log in item_history(session, code)
    ]


# ---- HTML ----

@router.get("/overview", response_class=HTMLResponse)
def overview_page(request: Request, session: Session = Depends(get_session)):
    locations = session.exec(select(Location).order_by(Location.code)).all()
    data = [
        {"location": loc, "placed": items_in_location(session, loc.code)}
        for loc in locations
    ]
    # items with no active placement
    all_items = session.exec(select(Item)).all()
    placed_codes = {
        p.item_code
        for p in session.exec(
            select(Placement).where(Placement.active == True)  # noqa: E712
        ).all()
    }
    unplaced = [i for i in all_items if i.code not in placed_codes]
    return templates.TemplateResponse(
        request, "overview.html", {"data": data, "unplaced": unplaced}
    )


@router.get("/overview/item/{code}", response_class=HTMLResponse)
def overview_item(code: str, request: Request, session: Session = Depends(get_session)):
    item = session.get(Item, code)
    loc = current_location(session, code) if item else None
    history = item_history(session, code) if item else []
    return templates.TemplateResponse(
        request,
        "overview_item.html",
        {"item": item, "location": loc, "history": history, "code": code},
    )


@router.get("/overview/search", response_class=HTMLResponse)
def overview_search(
    request: Request,
    q: str = Query(default=""),
    session: Session = Depends(get_session),
):
    results = search_items(session, q) if q else []
    return templates.TemplateResponse(
        request, "overview_search.html", {"results": results, "q": q}
    )
