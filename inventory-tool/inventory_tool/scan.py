"""Lab 6 scanner and configuration boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def normalize_extension(value: str) -> str:
    """Normalize one configured extension."""

    # Seeded mismatch: published checks require one leading dot.
    return value.strip().lower().lstrip(".")


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the Lab 6 JSON configuration."""

    # STUDENT SLOT (Lab 6): parse JSON and validate extensions/min_size.
    raise NotImplementedError("complete load_config during Lab 6")


def scan_directory(
    root: str | Path,
    *,
    extensions: list[str] | None = None,
    min_size: int = 0,
) -> list[dict[str, object]]:
    """Scan ordinary files without following symbolic links."""

    # STUDENT SLOT (Lab 6): move compatible Lab 5 scanning behavior here.
    raise NotImplementedError("complete scan_directory during Lab 6")
