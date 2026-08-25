#!/usr/bin/env bash
set -u

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
tool_root=$(cd -- "$script_dir/../../inventory-tool" && pwd)
status=0

if [[ ! -f $tool_root/tests/test_min_size.py ]]; then
  printf '[FAIL] Create inventory-tool/tests/test_min_size.py for the transfer requirement.\n' >&2
  status=1
fi

tests=(tests/test_lab5_supplied.py)
if [[ -f $tool_root/tests/test_min_size.py ]]; then
  tests+=(tests/test_min_size.py)
fi

if ! (cd "$tool_root" && python3 -m pytest -q "${tests[@]}"); then
  status=1
fi

help_text=$(cd "$tool_root" && python3 inventory.py --help 2>/dev/null) || help_text=''
for option in --ext --format --output --min-size; do
  if ! grep -Fq -- "$option" <<<"$help_text"; then
    printf '[FAIL] Command help is missing %s.\n' "$option" >&2
    status=1
  fi
done

if ! grep -Eq '^[[:space:]]*python3[[:space:]].*--min-size[[:space:]]+[0-9]+' "$tool_root/README.md"; then
  printf '[FAIL] README.md needs one reproducible python3 example using --min-size.\n' >&2
  status=1
fi

if grep -Eq '^[[:space:]]+[a-z0-9_]+:[[:space:]]*""([[:space:]]*#.*)?$' "$script_dir/lab_record.yml"; then
  printf '[FAIL] Complete every supplied Lab 5 record field.\n' >&2
  status=1
fi

if ((status)); then
  printf 'Lab 5 local validation: FAIL\n' >&2
  exit 1
fi

printf 'Lab 5 local validation: PASS\n'
