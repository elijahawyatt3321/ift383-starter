#!/usr/bin/env bash
set -u

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
tool_root=$(cd -- "$script_dir/../../inventory-tool" && pwd)
status=0

for student_test in test_min_size.py test_symlink_skip.py; do
  if [[ ! -f $tool_root/tests/$student_test ]]; then
    printf '[FAIL] Required student test is missing: inventory-tool/tests/%s\n' "$student_test" >&2
    status=1
  fi
done

tests=(tests/test_lab5_supplied.py tests/test_lab6_supplied.py)
[[ -f $tool_root/tests/test_min_size.py ]] && tests+=(tests/test_min_size.py)
[[ -f $tool_root/tests/test_symlink_skip.py ]] && tests+=(tests/test_symlink_skip.py)

if ! (cd "$tool_root" && python3 -m pytest -q "${tests[@]}"); then
  status=1
fi

help_text=$(cd "$tool_root" && python3 inventory.py --help 2>/dev/null) || help_text=''
for option in --config --log-file; do
  if ! grep -Fq -- "$option" <<<"$help_text"; then
    printf '[FAIL] Command help is missing %s.\n' "$option" >&2
    status=1
  fi
done

if ! grep -Eq '^[[:space:]]*python3[[:space:]].*--config[[:space:]]+' "$tool_root/README.md" \
  || ! grep -Eq '^[[:space:]]*python3[[:space:]].*--log-file[[:space:]]+' "$tool_root/README.md"; then
  printf '[FAIL] README.md needs reproducible python3 commands for --config and --log-file.\n' >&2
  status=1
fi

if grep -Eq '^[[:space:]]+[a-z0-9_]+:[[:space:]]*""([[:space:]]*#.*)?$' "$script_dir/lab_record.yml"; then
  printf '[FAIL] Complete every supplied Lab 6 record field.\n' >&2
  status=1
fi

if ((status)); then
  printf 'Lab 6 local validation: FAIL\n' >&2
  exit 1
fi

printf 'Lab 6 local validation: PASS\n'
