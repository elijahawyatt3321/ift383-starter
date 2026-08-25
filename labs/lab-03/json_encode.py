#!/usr/bin/env python3
"""Serialize the three guided Lab 3 values as one JSON object."""

from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "ERROR: expected total_requests, not_found_records, and top_404_path",
            file=sys.stderr,
        )
        return 2

    try:
        total_requests = int(sys.argv[1])
        not_found_records = int(sys.argv[2])
    except ValueError:
        print("ERROR: report counts must be integers", file=sys.stderr)
        return 2

    top_404_path = sys.argv[3] or None
    document = {
        "total_requests": total_requests,
        "not_found_records": not_found_records,
        "top_404_path": top_404_path,
    }
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
