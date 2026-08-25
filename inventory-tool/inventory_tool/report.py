"""Pure report-formatting functions supplied as a Lab 6 model."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


def ordered_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Copy records into deterministic name order."""

    return [dict(record) for record in sorted(records, key=lambda item: str(item["name"]))]


def format_table(records: Iterable[Mapping[str, Any]]) -> str:
    """Format ordinary inventory records as a tab-separated table."""

    lines = ["NAME\tSIZE\tEXTENSION"]
    for record in ordered_records(records):
        lines.append(f"{record['name']}\t{record['size']}\t{record['extension']}")
    return "\n".join(lines)


def format_json(records: Iterable[Mapping[str, Any]]) -> str:
    """Format ordinary inventory records as deterministic JSON."""

    return json.dumps(ordered_records(records), indent=2, sort_keys=True)
