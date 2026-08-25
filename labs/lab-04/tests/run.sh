#!/usr/bin/env bash

set -u

tests_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
lab_dir="$(cd -- "$tests_dir/.." && pwd -P)"
script="$lab_dir/logmaint.sh"
fixture="$lab_dir/fixture"
reset="$tests_dir/reset_fixture.sh"
scratch_dir="$(mktemp -d)" || {
  printf 'ERROR: could not create test workspace.\n' >&2
  exit 1
}
trap 'rm -rf -- "$scratch_dir"' EXIT

passes=0
failures=0

pass() {
  ((passes += 1))
  printf 'PASS: %s\n' "$1"
}

fail() {
  ((failures += 1))
  printf 'FAIL: %s\n' "$1"
}

if bash -n "$script"; then
  pass 'script has valid Bash syntax'
else
  fail 'script has valid Bash syntax'
fi

bash "$reset" >/dev/null
rm -f -- "$lab_dir/last_run.json"
for path in \
  "$fixture/keep.txt" \
  "$fixture/old api.log" \
  "$fixture/old-app.log" \
  "$fixture/recent-app.log"; do
  cksum "$path"
done > "$scratch_dir/hashes.before"
bash "$script" --dir "$fixture" --days 7 --dry-run \
  > "$scratch_dir/dry.out" 2> "$scratch_dir/dry.err"
dry_status=$?
for path in \
  "$fixture/keep.txt" \
  "$fixture/old api.log" \
  "$fixture/old-app.log" \
  "$fixture/recent-app.log"; do
  cksum "$path"
done > "$scratch_dir/hashes.after"
if (( dry_status == 0 )) && cmp -s "$scratch_dir/hashes.before" "$scratch_dir/hashes.after"; then
  pass 'dry-run leaves every fixture file unchanged'
else
  fail 'dry-run leaves every fixture file unchanged'
fi

if python3 - "$lab_dir/last_run.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    report = json.load(source)

expected_keys = {"mode", "selected", "succeeded", "failed", "success"}
assert set(report) == expected_keys
assert report["mode"] == "dry-run"
assert report["selected"] == 2
assert report["succeeded"] == 2
assert report["failed"] == 0
assert report["success"] is True
PY
then
  pass 'dry-run writes the required valid JSON summary'
else
  fail 'dry-run writes the required valid JSON summary'
fi

bash "$reset" >/dev/null
sed -n 's/^WOULD_COMPRESS //p' "$scratch_dir/dry.out" |
  LC_ALL=C sort > "$scratch_dir/dry.paths"
bash "$script" --dir "$fixture" --days 7 --apply \
  > "$scratch_dir/apply.out" 2> "$scratch_dir/apply.err"
apply_status=$?
sed -n 's/^COMPRESSED //p' "$scratch_dir/apply.out" |
  LC_ALL=C sort > "$scratch_dir/apply.paths"
if (( apply_status == 0 )) &&
   [[ -f "$fixture/old-app.log.gz" ]] &&
   [[ -f "$fixture/old api.log.gz" ]] &&
   cmp -s "$scratch_dir/dry.paths" "$scratch_dir/apply.paths"; then
  pass 'apply uses the dry-run selection and preserves spaced paths'
else
  fail 'apply uses the dry-run selection and preserves spaced paths'
fi

bash "$reset" >/dev/null
mkdir -p "$scratch_dir/failing-bin"
cat > "$scratch_dir/failing-bin/gzip" <<'FAKE'
#!/usr/bin/env bash
exit 9
FAKE
chmod 700 "$scratch_dir/failing-bin/gzip"
PATH="$scratch_dir/failing-bin:$PATH" \
  bash "$script" --dir "$fixture" --days 7 --apply \
  > "$scratch_dir/failure.out" 2> "$scratch_dir/failure.err"
forced_status=$?
if (( forced_status != 0 )); then
  pass 'a compression failure produces a nonzero final status'
else
  fail 'a compression failure produces a nonzero final status'
fi

bash "$reset" >/dev/null
bash "$script" --dir "$fixture" --days 7 --dry-run --apply \
  > "$scratch_dir/arguments.out" 2> "$scratch_dir/arguments.err"
argument_status=$?
if (( argument_status != 0 )); then
  pass 'conflicting mode arguments are rejected'
else
  fail 'conflicting mode arguments are rejected'
fi

printf '\nResult: %s passed; %s failed.\n' "$passes" "$failures"
if (( failures > 0 )); then
  printf 'The untouched starter is expected to fail the action-boundary and JSON-report checks.\n'
  exit 1
fi
printf 'All published Lab 4 checks passed.\n'
