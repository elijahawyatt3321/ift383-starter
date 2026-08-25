#!/usr/bin/env bash
set -euo pipefail

tool_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
fixture="$tool_root/fixtures/base"

printf 'Fixture paths (quoted so spaces and punctuation remain visible):\n'
find "$fixture" -mindepth 1 -maxdepth 2 -printf '  %P\n' | LC_ALL=C sort

printf '\nStarting table from the fixture directory:\n'
printf 'Command: python3 "%s" .\n' "$tool_root/inventory.py"
cd "$fixture"
python3 "$tool_root/inventory.py" .
