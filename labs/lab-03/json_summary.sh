#!/usr/bin/env bash

set -u
export LC_ALL=C

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
input_file="${1:-$script_dir/access.log}"

if [[ ! -f "$input_file" ]]; then
  printf 'ERROR: input log does not exist: %s\n' "$input_file" >&2
  exit 2
fi

# GUIDED JSON SLOT 1 OF 3
# Replace the next assignment with an awk command substitution that counts all
# input records and always produces a number.
total_requests='STUDENT_SLOT_1'

# GUIDED JSON SLOT 2 OF 3
# Replace the next assignment with an awk command substitution that counts only
# records whose exact ninth field is 404.
not_found_records='STUDENT_SLOT_2'

# GUIDED JSON SLOT 3 OF 3
# Replace the next assignment with the guided pipeline that finds the most
# frequent 404 API path. An empty result is allowed when no record matches.
top_404_path='STUDENT_SLOT_3'

# The supplied helper performs safe JSON serialization. Do not replace it with
# hand-built JSON text.
python3 "$script_dir/json_encode.py" \
  "$total_requests" "$not_found_records" "$top_404_path"
