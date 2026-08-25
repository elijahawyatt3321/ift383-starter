#!/usr/bin/env bash

set -u

usage() {
  printf 'Usage: %s --dir DIRECTORY --days DAYS (--dry-run | --apply)\n' "$0" >&2
}

argument_error() {
  printf 'ERROR: %s\n' "$1" >&2
  usage
  exit 64
}

target_dir=''
days=''
mode=''

while (( $# > 0 )); do
  case "$1" in
    --dir)
      (( $# >= 2 )) || argument_error '--dir requires a value'
      target_dir="$2"
      shift 2
      ;;
    --days)
      (( $# >= 2 )) || argument_error '--days requires a value'
      days="$2"
      shift 2
      ;;
    --dry-run)
      [[ -z "$mode" ]] || argument_error 'choose exactly one mode'
      mode='dry-run'
      shift
      ;;
    --apply)
      [[ -z "$mode" ]] || argument_error 'choose exactly one mode'
      mode='apply'
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      argument_error "unknown argument: $1"
      ;;
  esac
done

[[ -n "$target_dir" ]] || argument_error '--dir is required'
[[ -n "$days" ]] || argument_error '--days is required'
[[ -n "$mode" ]] || argument_error 'one mode is required'
[[ "$days" =~ ^[0-9]+$ ]] || argument_error '--days must be a nonnegative integer'

if [[ ! -d "$target_dir" ]]; then
  printf 'ERROR: directory does not exist: %s\n' "$target_dir" >&2
  exit 66
fi

if ! target_dir_absolute="$(cd -- "$target_dir" && pwd -P)"; then
  printf 'ERROR: cannot resolve directory: %s\n' "$target_dir" >&2
  exit 66
fi

if [[ "$target_dir_absolute" == '/' ||
      "$target_dir_absolute" == '/home' ||
      ( -n "${HOME:-}" && "$target_dir_absolute" == "$HOME" ) ]]; then
  printf 'ERROR: refusing unsafe broad directory: %s\n' "$target_dir_absolute" >&2
  exit 77
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
run_log="$script_dir/run.log"

# STUDENT JSON REPORT BOUNDARY (Lab 4)
# After the guided lesson, define report_file beside run_log and write the
# current run's controlled values as a valid top-level JSON object.

process_path() {
  local path="$1"

  if [[ "$mode" == 'dry-run' ]]; then
    printf 'WOULD_COMPRESS %s\n' "$path"
    return 0
  fi

  # STUDENT ACTION BOUNDARY
  # The next branch contains the two bounded defects described by the tests.
  # Repair the command invocation and the failure status without changing the
  # shared selector or adding a second selection path.
  if gzip $path; then
    printf 'COMPRESSED %s\n' "$path"
    return 0
  else
    printf 'ERROR: compression failed: %s\n' "$path" >&2
    return 0
  fi
}

selected=0
succeeded=0
failed=0

while IFS= read -r -d '' path; do
  ((selected += 1))
  if process_path "$path"; then
    ((succeeded += 1))
  else
    ((failed += 1))
  fi
done < <(
  find "$target_dir_absolute" -maxdepth 1 -type f -name '*.log' \
    -mtime +"$days" -print0
)

timestamp="$(date '+%Y-%m-%dT%H:%M:%S%z')"
if (( failed > 0 )); then
  final_status=1
else
  final_status=0
fi

# STUDENT JSON REPORT BOUNDARY (Lab 4)
# Write mode, selected, succeeded, failed, and success before exiting.
# Generate the values from this run; do not hard-code observed output.

summary="${timestamp} mode=${mode} dir=${target_dir_absolute} days=${days} selected=${selected} succeeded=${succeeded} failed=${failed} status=${final_status}"
printf '%s\n' "$summary" | tee -a "$run_log"
exit "$final_status"
