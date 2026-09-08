"""Label endpoints: choose locations/items and download an A4 PDF sheet."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session, select

from app.db import get_session
from app.labels import LabelSpec, render_command_sheet, render_label_sheet
from app.models import Item, Location
from app.templates import templates

router = APIRouter()


def _specs_for(session: Session, loc_codes: list[str], item_codes: list[str]) -> list[LabelSpec]:
    specs: list[LabelSpec] = []
    for code in loc_codes:
        loc = session.get(Location, code)
        if loc:
            specs.append(LabelSpec(payload=loc.code, caption=loc.name))
    for code in item_codes:
        item = session.get(Item, code)
        if item:
            specs.append(LabelSpec(payload=item.code, caption=item.title))
    return specs


@router.get("/labels", response_class=HTMLResponse)
def labels_page(request: Request, session: Session = Depends(get_session)):
    locations = session.exec(select(Location).order_by(Location.code)).all()
    items = session.exec(select(Item).order_by(Item.code)).all()
    return templates.TemplateResponse(
        request, "labels.html", {"locations": locations, "items": items}
    )


@router.get("/labels/commands/pdf")
def command_labels_pdf():
    pdf = render_command_sheet()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="commands.pdf"'},
    )


@router.get("/labels/pdf")
def labels_pdf(
    loc: list[str] = Query(default=[]),
    item: list[str] = Query(default=[]),
    session: Session = Depends(get_session),
):
    specs = _specs_for(session, loc, item)
    if not specs:
        # Fall back to all locations + items so the endpoint is never empty.
        locations = session.exec(select(Location)).all()
        items = session.exec(select(Item)).all()
        specs = [LabelSpec(payload=l.code, caption=l.name) for l in locations]
        specs += [LabelSpec(payload=i.code, caption=i.title) for i in items]
    pdf = render_label_sheet(specs)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="labels.pdf"'},
    )
