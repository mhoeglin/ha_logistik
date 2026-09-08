"""Item (box/article) CRUD: REST + HTML GUI, optional content lines & photos."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.codes import format_item_code
from app.config import settings
from app.db import get_session
from app.models import Item, ItemContent, ItemType, Photo
from app.templates import templates

router = APIRouter()

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class ContentLine(BaseModel):
    text: str
    quantity: int = 1


class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: ItemType = ItemType.box
    contents: list[ContentLine] = []


class ItemRead(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    type: ItemType


def _next_item_code(session: Session) -> str:
    codes = session.exec(select(Item.code)).all()
    max_num = 0
    for c in codes:
        try:
            n = int(c.split(":", 1)[1])
            max_num = max(max_num, n)
        except (IndexError, ValueError):
            continue
    return format_item_code(max_num + 1)


def create_item(session: Session, data: ItemCreate) -> Item:
    item = Item(
        code=_next_item_code(session),
        title=data.title,
        description=data.description,
        type=data.type,
    )
    session.add(item)
    for line in data.contents:
        if line.text.strip():
            session.add(
                ItemContent(
                    item_code=item.code,
                    text=line.text.strip(),
                    quantity=line.quantity,
                )
            )
    session.commit()
    session.refresh(item)
    return item


def save_photo(session: Session, item_code: str, upload: UploadFile) -> Photo:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="unsupported image type")
    settings.ensure_dirs()
    fname = f"{item_code.replace(':', '_')}_{uuid.uuid4().hex[:8]}{suffix}"
    dest = settings.photos_dir / fname
    with dest.open("wb") as f:
        f.write(upload.file.read())
    photo = Photo(item_code=item_code, path=str(dest))
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


# ---- REST API ----

@router.post("/api/items", response_model=ItemRead, status_code=201)
def api_create_item(
    data: ItemCreate, session: Session = Depends(get_session)
) -> Item:
    return create_item(session, data)


@router.get("/api/items", response_model=list[ItemRead])
def api_list_items(session: Session = Depends(get_session)) -> list[Item]:
    return session.exec(select(Item).order_by(Item.code)).all()


@router.get("/api/items/{code}", response_model=ItemRead)
def api_get_item(code: str, session: Session = Depends(get_session)) -> Item:
    item = session.get(Item, code)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


# ---- HTML GUI ----

@router.get("/items", response_class=HTMLResponse)
def html_list_items(request: Request, session: Session = Depends(get_session)):
    items = session.exec(select(Item).order_by(Item.code)).all()
    return templates.TemplateResponse(
        request, "items.html", {"items": items, "item_types": list(ItemType)}
    )


@router.post("/items")
async def html_create_item(
    title: str = Form(...),
    description: str = Form(""),
    type: str = Form("box"),
    content_text: list[str] = Form(default=[]),
    content_qty: list[str] = Form(default=[]),
    photo: UploadFile | None = File(default=None),
    session: Session = Depends(get_session),
):
    contents: list[ContentLine] = []
    for i, text in enumerate(content_text):
        if text and text.strip():
            try:
                qty = int(content_qty[i]) if i < len(content_qty) and content_qty[i] else 1
            except ValueError:
                qty = 1
            contents.append(ContentLine(text=text, quantity=qty))

    try:
        item_type = ItemType(type)
    except ValueError:
        item_type = ItemType.box

    item = create_item(
        session,
        ItemCreate(
            title=title,
            description=description or None,
            type=item_type,
            contents=contents,
        ),
    )
    if photo is not None and photo.filename:
        save_photo(session, item.code, photo)

    return RedirectResponse(url=f"/items/{item.code}", status_code=303)


@router.get("/photos/{photo_id}")
def serve_photo(photo_id: int, session: Session = Depends(get_session)):
    from fastapi.responses import FileResponse

    photo = session.get(Photo, photo_id)
    if photo is None or not Path(photo.path).exists():
        raise HTTPException(status_code=404, detail="photo not found")
    return FileResponse(photo.path)


@router.get("/items/{code}", response_class=HTMLResponse)
def html_item_detail(
    code: str, request: Request, session: Session = Depends(get_session)
):
    item = session.get(Item, code)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    contents = session.exec(
        select(ItemContent).where(ItemContent.item_code == code)
    ).all()
    photos = session.exec(select(Photo).where(Photo.item_code == code)).all()
    return templates.TemplateResponse(
        request,
        "item_detail.html",
        {"item": item, "contents": contents, "photos": photos},
    )
