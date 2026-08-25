#!/usr/bin/env bash
set -euo pipefail

fixture_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/data" && pwd)
TZ=UTC0 touch -t 202608201200.00 "$fixture_dir/fresh.log"
TZ=UTC0 touch -t 202607010830.00 "$fixture_dir/stale.log"
TZ=UTC0 touch -t 202606151745.00 "$fixture_dir/archive.dat"
TZ=UTC0 touch -t 202608100900.00 "$fixture_dir/keep.txt"
printf 'Reset four bounded fixture timestamps.\n'
