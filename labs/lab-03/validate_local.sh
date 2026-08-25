#!/usr/bin/env bash

set -u
export LC_ALL=C

lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
scratch_dir="$(mktemp -d)" || {
  printf 'ERROR: could not create a bounded validation directory.\n' >&2
  exit 1
}
trap 'rm -rf -- "$scratch_dir"' EXIT

passes=0
failures=0

pass() {
  ((passes += 1))
  printf 'PASS: %s\n' "$1"
}

fail() {
  ((failures += 1))
  printf 'FAIL: %s\n' "$1"
}

if bash -n "$lab_dir/pipeline_probes.sh" &&
   bash -n "$lab_dir/toptalkers.sh" &&
   bash -n "$lab_dir/scan_report.sh" &&
   bash -n "$lab_dir/json_summary.sh"; then
  pass 'Lab 3 scripts have valid Bash syntax'
else
  fail 'Lab 3 scripts have valid Bash syntax'
fi

fixture_hash="$(sha256sum "$lab_dir/access.log" | awk '{print $1}')"
if [[ "$fixture_hash" == 'ef9fc8a63d298764d22bfcaf00d97007e45a5fe898a6cac20fc1488f27c1a5ff' ]]; then
  pass 'common access-log fixture is unchanged'
else
  fail 'common access-log fixture is unchanged'
fi

serializer_hash="$(sha256sum "$lab_dir/json_encode.py" | awk '{print $1}')"
if [[ "$serializer_hash" == '8d7e399a321750a354abe295c43f0ea6e8a9d1ecff3179363232c87671a9cdf4' ]]; then
  pass 'supplied JSON serializer is unchanged'
else
  fail 'supplied JSON serializer is unchanged'
fi

if grep -q 'STUDENT_SLOT' "$lab_dir/scan_report.sh" ||
   grep -q 'STUDENT_SLOT' "$lab_dir/json_summary.sh"; then
  fail 'report, transfer, and guided JSON slots are complete'
else
  pass 'report, transfer, and guided JSON slots are complete'
fi

(
  cd -- "$scratch_dir" || exit 1
  "$lab_dir/toptalkers.sh"
) > "$scratch_dir/toptalkers.out" 2> "$scratch_dir/toptalkers.err"
toptalkers_status=$?
if (( toptalkers_status == 0 )) &&
   python3 - "$lab_dir/access.log" "$scratch_dir/toptalkers.out" '' <<'PY'
from collections import Counter
from pathlib import Path
import sys

fixture_path, result_path, status_filter = sys.argv[1:]
records = [line.split() for line in Path(fixture_path).read_text().splitlines()]
if status_filter:
    records = [record for record in records if record[8] == status_filter]
expected_counts = Counter(record[0] for record in records)
expected = sorted(
    ((count, client) for client, count in expected_counts.items()),
    key=lambda row: (-row[0], row[1]),
)
actual = []
try:
    for line in Path(result_path).read_text().splitlines():
        parts = line.split()
        if len(parts) != 2:
            raise ValueError
        actual.append((int(parts[0]), parts[1]))
except (ValueError, IndexError):
    print("Use one 'count client' row per client with no blank rows.", file=sys.stderr)
    raise SystemExit(1)
if actual != expected:
    print("Check client counts, the optional exact-status filter, and deterministic tie order.", file=sys.stderr)
    raise SystemExit(1)
PY
then
  pass 'no-argument top-talkers result is deterministic from any directory'
else
  fail 'no-argument top-talkers result is deterministic from any directory'
fi

(
  cd -- "$scratch_dir" || exit 1
  "$lab_dir/toptalkers.sh" 404
) > "$scratch_dir/toptalkers-404.out" 2> "$scratch_dir/toptalkers-404.err"
status_404=$?
if (( status_404 == 0 )) &&
   python3 - "$lab_dir/access.log" "$scratch_dir/toptalkers-404.out" '404' <<'PY'
from collections import Counter
from pathlib import Path
import sys

fixture_path, result_path, status_filter = sys.argv[1:]
records = [line.split() for line in Path(fixture_path).read_text().splitlines()]
records = [record for record in records if record[8] == status_filter]
counts = Counter(record[0] for record in records)
expected = sorted(((count, client) for client, count in counts.items()), key=lambda row: (-row[0], row[1]))
try:
    actual = [(int(parts[0]), parts[1]) for parts in (line.split() for line in Path(result_path).read_text().splitlines()) if len(parts) == 2]
except (ValueError, IndexError):
    raise SystemExit(1)
if actual != expected:
    print("Check that the optional argument filters only the exact status field and preserves tie order.", file=sys.stderr)
    raise SystemExit(1)
PY
then
  pass 'optional exact-status filter preserves required ordering'
else
  fail 'optional exact-status filter preserves required ordering'
fi

"$lab_dir/toptalkers.sh" 99 > "$scratch_dir/invalid.out" 2> "$scratch_dir/invalid.err"
invalid_status=$?
if (( invalid_status != 0 )); then
  pass 'invalid status argument is rejected'
else
  fail 'invalid status argument is rejected'
fi

(
  cd -- "$scratch_dir" || exit 1
  "$lab_dir/scan_report.sh" "$lab_dir/access.log"
) > "$scratch_dir/report.out" 2> "$scratch_dir/report.err"
report_status=$?
if (( report_status == 0 )) &&
   python3 - "$lab_dir/access.log" "$scratch_dir/report.out" <<'PY'
from collections import Counter
from pathlib import Path
import sys

fixture_path, report_path = sys.argv[1:]
records = [line.split() for line in Path(fixture_path).read_text().splitlines()]

status_counts = Counter(int(record[8]) for record in records)
api_404_counts = Counter(
    record[6] for record in records
    if record[8] == "404" and record[6].startswith("/api/")
)
server_error_counts = Counter(
    record[0] for record in records
    if 500 <= int(record[8]) <= 599
)

ranked_api = sorted(api_404_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
ranked_clients = sorted(server_error_counts.items(), key=lambda item: (-item[1], item[0]))[:5]

expected = ["TOTAL REQUESTS", str(len(records)), "", "STATUS COUNTS"]
expected.extend(f"{status} {status_counts[status]}" for status in sorted(status_counts))
expected.extend(["", "TOP 404 API PATHS"])
expected.extend(f"{count} {path}" for path, count in ranked_api)
expected.extend(["", "SERVER ERROR CLIENTS"])
expected.extend(f"{count} {client}" for client, count in ranked_clients)

actual = Path(report_path).read_text().splitlines()
if actual != expected:
    print("Check all four headings, field-aware counts, row format, five-row limits, and tie order.", file=sys.stderr)
    raise SystemExit(1)
PY
then
  pass 'four-section report matches the published fixture contract'
else
  fail 'four-section report matches the published fixture contract'
fi

if [[ -s "$lab_dir/findings.txt" ]] && cmp -s "$scratch_dir/report.out" "$lab_dir/findings.txt"; then
  pass 'saved findings reproduce the current report byte for byte'
else
  fail 'saved findings reproduce the current report byte for byte'
fi

(
  cd -- "$scratch_dir" || exit 1
  "$lab_dir/json_summary.sh" "$lab_dir/access.log"
) > "$scratch_dir/summary.json" 2> "$scratch_dir/summary.err"
json_status=$?
if (( json_status == 0 )) &&
   [[ ! -s "$scratch_dir/summary.err" ]] &&
   python3 - "$scratch_dir/summary.json" <<'PY'
import json
from pathlib import Path
import sys

try:
    document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    raise SystemExit(1)

expected = {
    "total_requests": 24,
    "not_found_records": 7,
    "top_404_path": "/api/items",
}
if document != expected:
    raise SystemExit(1)
PY
then
  pass 'guided summary emits one exact top-level JSON object'
else
  fail 'guided summary emits one exact top-level JSON object'
fi

if [[ -s "$lab_dir/summary.json" ]] && cmp -s "$scratch_dir/summary.json" "$lab_dir/summary.json"; then
  pass 'saved JSON summary reproduces the current output byte for byte'
else
  fail 'saved JSON summary reproduces the current output byte for byte'
fi

"$lab_dir/json_summary.sh" "$scratch_dir/missing.log" \
  > "$scratch_dir/missing.json" 2> "$scratch_dir/missing.err"
missing_status=$?
if (( missing_status != 0 )) &&
   [[ ! -s "$scratch_dir/missing.json" ]] &&
   [[ -s "$scratch_dir/missing.err" ]]; then
  pass 'JSON input errors stay off standard output'
else
  fail 'JSON input errors stay off standard output'
fi

if awk '
  /^[[:space:]]+[a-z0-9_]+:/ {
    value=$0
    sub(/^[^:]+:[[:space:]]*/, "", value)
    gsub(/[[:space:]"\047]/, "", value)
    if (value == "") empty=1
  }
  END {exit(empty ? 0 : 1)}
' "$lab_dir/lab_record.yml"; then
  fail 'structured response fields are complete'
else
  pass 'structured response fields are complete'
fi

printf '\nResult: %s passed; %s failed.\n' "$passes" "$failures"
(( failures == 0 ))
