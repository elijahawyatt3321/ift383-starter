#!/usr/bin/env bash

set -u

scratch_dir="$(mktemp -d)" || {
  printf 'ERROR: could not create a temporary probe directory.\n' >&2
  exit 1
}
trap 'rm -rf -- "$scratch_dir"' EXIT

cat > "$scratch_dir/probe.log" <<'DATA'
192.0.2.10 - - [23/Aug/2026:07:00:01 +0000] "GET /docs/404-guide HTTP/1.1" 200 404
192.0.2.11 - - [23/Aug/2026:07:00:02 +0000] "GET /api/items HTTP/1.1" 404 190
DATA

whole_line_count="$(grep -c '404' "$scratch_dir/probe.log")"
status_field_count="$(awk '$9 == 404 {count++} END {print count + 0}' "$scratch_dir/probe.log")"

printf 'Whole-line matches for 404: %s\n' "$whole_line_count"
printf 'Exact field-9 matches for 404: %s\n' "$status_field_count"
if [[ "$whole_line_count" == "$status_field_count" ]]; then
  printf 'OBSERVATION q1=same\n'
else
  printf 'OBSERVATION q1=different\n'
fi

printf '\nDefault text sort of the values 2 and 10:\n'
printf '2\n10\n' | LC_ALL=C sort
printf 'Numeric sort of the values 2 and 10:\n'
printf '2\n10\n' | LC_ALL=C sort -n
printf 'OBSERVATION q2=no\n'
