#!/usr/bin/env bash

set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
lab_dir="$(cd -- "$script_dir/.." && pwd -P)"
scratch_dir="$(mktemp -d)" || {
  printf 'ERROR: could not create a temporary practice directory.\n' >&2
  exit 1
}
trap 'rm -rf -- "$scratch_dir"' EXIT

if [[ -x "$lab_dir/broken_greeting.sh" ]]; then
  greeting_observation='runs'
else
  greeting_observation='permission-denied'
fi

printf 'practice data\n' > "$scratch_dir/source file.txt"
cp -- "$scratch_dir/source file.txt" "$scratch_dir/copied file.txt"

if [[ -f "$scratch_dir/source file.txt" ]]; then
  copy_kept_source='yes'
else
  copy_kept_source='no'
fi

mv -- "$scratch_dir/source file.txt" "$scratch_dir/moved file.txt"

if [[ -e "$scratch_dir/source file.txt" ]]; then
  move_kept_source='yes'
else
  move_kept_source='no'
fi

printf 'Greeting execute check: %s\n' "$greeting_observation"
printf 'Source remains after copy: %s\n' "$copy_kept_source"
printf 'Source remains after move: %s\n' "$move_kept_source"
printf 'OBSERVATION q1=%s\n' "$greeting_observation"
printf 'OBSERVATION q2=copy\n'
