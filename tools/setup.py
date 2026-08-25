#!/usr/bin/env python3
"""Configure private local identity data for IFT 383 submissions."""

from __future__ import annotations

import argparse
import sys

from ift383lib.common import CourseError, course_root, save_identity
from ift383lib.receipt import ensure_device_secret


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Store IFT 383 Canvas identity locally; no network access is used."
    )
    parser.add_argument(
        "--canvas-login",
        help="Canvas login / ASURITE UserID, not numeric student ID (prompted when omitted)",
    )
    parser.add_argument("--name", help="Student display name (prompted when omitted)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canvas_login = args.canvas_login or input("Canvas login / ASURITE UserID: ")
    display_name = args.name or input("Student display name: ")
    root = course_root()
    identity = save_identity(root, canvas_login, display_name)
    key = ensure_device_secret()
    print("IFT 383 local setup is complete.")
    print(f"Identity saved outside tracked course files at: {identity}")
    print(f"Installation key saved privately at: {key}")
    print("Neither file is tracked by Git. Identity values are copied into each Canvas ZIP; the secret key is never submitted.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CourseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
