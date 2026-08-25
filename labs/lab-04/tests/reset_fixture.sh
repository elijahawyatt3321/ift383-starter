#!/usr/bin/env bash

set -u

tests_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
fixture_dir="$(cd -- "$tests_dir/../fixture" && pwd -P)"

rm -f -- \
  "$fixture_dir/old-app.log.gz" \
  "$fixture_dir/old api.log.gz" \
  "$fixture_dir/recent-app.log.gz"

cat > "$fixture_dir/old-app.log" <<'DATA'
2026-08-13T09:00:00Z INFO inventory service started
2026-08-13T09:04:11Z WARN retry threshold reached
DATA

cat > "$fixture_dir/old api.log" <<'DATA'
2026-08-13T09:01:00Z INFO API listener ready
2026-08-13T09:05:42Z ERROR demonstration request failed
DATA

cat > "$fixture_dir/recent-app.log" <<'DATA'
2026-08-21T14:20:00Z INFO recent fixture entry
DATA

cat > "$fixture_dir/keep.txt" <<'DATA'
This non-log file must never be selected for compression.
DATA

python3 - "$fixture_dir" <<'PY'
import os
import sys
import time

fixture = sys.argv[1]
now = time.time()
ages = {
    "old-app.log": 10,
    "old api.log": 10,
    "recent-app.log": 2,
    "keep.txt": 10,
}
for name, age_days in ages.items():
    timestamp = now - (age_days * 24 * 60 * 60)
    os.utime(os.path.join(fixture, name), (timestamp, timestamp))
PY

printf 'Fixture reset: two old .log files, one recent .log file, one non-log file.\n'
