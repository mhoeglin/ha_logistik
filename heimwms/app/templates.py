"""Shared Jinja2 templates instance.

Ingress support: Home Assistant serves the add-on under a path prefix and
sends it in the `X-Ingress-Path` header. All in-app URLs must be prefixed
with that value so links resolve correctly both behind Ingress and when the
app is reached directly on its port (where the header is absent -> "").
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def base_url(request: Request) -> str:
    """Return the URL prefix to use for in-app links.

    Behind HA Ingress this is the value of the X-Ingress-Path header
    (e.g. "/api/hassio_ingress/<token>"); otherwise an empty string.
    """
    return request.headers.get("X-Ingress-Path", "") if request else ""


templates.env.globals["base_url"] = base_url
