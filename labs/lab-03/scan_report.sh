#!/usr/bin/env bash

set -u
export LC_ALL=C

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
input_file="${1:-$script_dir/access.log}"

if [[ ! -f "$input_file" ]]; then
  printf 'ERROR: input log does not exist: %s\n' "$input_file" >&2
  exit 2
fi

printf 'TOTAL REQUESTS\n'
# CORE STUDENT SLOT 1 OF 3
# Replace the next command with a pipeline that prints one number.
printf 'STUDENT_SLOT_1\n'

printf '\nSTATUS COUNTS\n'
# CORE STUDENT SLOT 2 OF 3
# Replace the next command with a pipeline that prints "status count" rows.
printf 'STUDENT_SLOT_2\n'

printf '\nTOP 404 API PATHS\n'
# CORE STUDENT SLOT 3 OF 3
# Replace the next command with the required field-aware top-five pipeline.
printf 'STUDENT_SLOT_3\n'

printf '\nSERVER ERROR CLIENTS\n'
# INDEPENDENT TRANSFER SLOT
# Replace the next command with your distinct 500-through-599 client pipeline.
printf 'STUDENT_TRANSFER_SLOT\n'
