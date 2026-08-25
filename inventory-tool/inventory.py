#!/usr/bin/env python3
"""Lab 5 starting point for the continuing inventory command-line tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence


def extension_for(path: Path) -> str:
    """Return the displayed extension for one path."""

    # Seeded defect: extensionless files are labeled incorrectly.
    return path.suffix[1:] if path.suffix else path.name


def scan_directory(directory: str | Path) -> list[dict[str, object]]:
    """Return one record per ordinary file in the requested directory."""

    # Seeded defect: the supplied directory is not yet used as the scan root.
    root = Path.cwd()
    records: list[dict[str, object]] = []
    for item in sorted(root.iterdir(), key=lambda candidate: candidate.name):
        if item.is_file():
            records.append(
                {
                    "name": item.name,
                    "size": item.stat().st_size,
                    "extension": extension_for(item),
                }
            )
    return records


def render_table(records: list[dict[str, object]]) -> str:
    lines = ["NAME\tSIZE\tEXTENSION"]
    for record in records:
        lines.append(f"{record['name']}\t{record['size']}\t{record['extension']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report ordinary files in one directory.")
    parser.add_argument("directory", help="directory to inspect")

    # STUDENT SLOT (Lab 5): add --ext, --format, and --output here.
    # STUDENT SLOT (Lab 5 transfer): add --min-size after base behavior works.
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # STUDENT SLOT (Lab 5): validate the requested directory and apply options.
    try:
        records = scan_directory(args.directory)
    except OSError as exc:
        print(f"inventory: {exc}", file=sys.stderr)
        return 2

    # STUDENT SLOT (Lab 5): select table or JSON and honor --output.
    print(render_table(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
