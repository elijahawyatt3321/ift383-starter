#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"

printf 'Configure this single entry point to run the project tests.\n' >&2
printf 'It must exit nonzero when any test fails.\n' >&2
exit 2
