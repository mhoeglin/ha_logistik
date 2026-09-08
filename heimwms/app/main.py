"""FastAPI application entry point for Heim-WMS."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB initialisation is wired in Task 2; keep the hook here.
    try:
        from app.db import init_db

        init_db()
    except Exception:  # pragma: no cover - db module may not exist yet
        pass

    # Optional demo seeding, controlled by env (used by the HA add-on option).
    import os

    if os.getenv("HEIMWMS_SEED", "").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            from scripts.seed import main as seed_main

            seed_main()
        except Exception as exc:  # pragma: no cover - seeding is best-effort
            print(f"[heimwms] seeding skipped/failed: {exc}")
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Heim-WMS", version=__version__, lifespan=lifespan)

    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    from fastapi.responses import RedirectResponse

    @app.get("/", include_in_schema=False)
    def root(request: Request):
        base = request.headers.get("X-Ingress-Path", "")
        return RedirectResponse(url=f"{base}/locations")

    from app.routers import help, items, labels, locations, overview, scan

    app.include_router(locations.router)
    app.include_router(items.router)
    app.include_router(labels.router)
    app.include_router(scan.router)
    app.include_router(overview.router)
    app.include_router(help.router)

    return app


app = create_app()
