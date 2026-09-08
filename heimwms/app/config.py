"""Application configuration, driven by environment variables."""
from __future__ import annotations

import os
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings resolved from the environment.

    All persistent artefacts (SQLite DB, uploaded photos, generated PDFs)
    live under DATA_DIR so a single Docker volume can persist everything.
    """

    def __init__(self) -> None:
        self.data_dir: Path = Path(os.getenv("HEIMWMS_DATA_DIR", "./data")).resolve()
        self.db_path: Path = Path(
            os.getenv("HEIMWMS_DB_PATH", str(self.data_dir / "heimwms.db"))
        )
        self.photos_dir: Path = Path(
            os.getenv("HEIMWMS_PHOTOS_DIR", str(self.data_dir / "photos"))
        )
        self.echo_sql: bool = _bool_env("HEIMWMS_ECHO_SQL", False)

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.photos_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
