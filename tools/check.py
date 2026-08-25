#!/usr/bin/env python3
"""Run safe, visible structural checks for one IFT 383 assignment."""

from __future__ import annotations

import argparse
import json
import sys

from ift383lib.common import (
    ASSIGNMENT_PATHS,
    CourseError,
    course_root,
    require_assignment,
    run_visible_checks,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run visible IFT 383 assignment checks.")
    parser.add_argument("assignment", choices=tuple(ASSIGNMENT_PATHS))
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assignment = require_assignment(args.assignment)
    results = run_visible_checks(course_root(), assignment)
    passed = all(result.passed for result in results)
    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "course": "IFT383",
                    "assignment": assignment,
                    "passed": passed,
                    "results": [result.as_dict() for result in results],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for result in results:
            label = "PASS" if result.passed else "FAIL"
            print(f"[{label}] {result.result_id}: {result.message}")
        print(f"Visible checks: {'PASS' if passed else 'FAIL'} ({sum(r.passed for r in results)}/{len(results)})")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CourseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
