"""Lab 6 command-line boundary signatures."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build the compatible inventory argument parser."""

    parser = argparse.ArgumentParser(description="Report ordinary files in one directory.")
    # STUDENT SLOT (Lab 6): move the compatible Lab 5 arguments here.
    # STUDENT SLOT (Lab 6): add --config and --log-file.
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, dispatch scanning, and write the selected report."""

    # STUDENT SLOT (Lab 6): connect parser, scanner, report, and logging boundaries.
    build_parser().parse_args(argv)
    return 2
