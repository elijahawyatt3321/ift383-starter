#!/usr/bin/env bash

set -u

lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(git -C "$lab_dir" rev-parse --show-toplevel 2>/dev/null)" || {
  printf 'FAIL: Lab 4 validation must run inside the course Git repository.\n' >&2
  exit 1
}
passes=0
failures=0
run_log_was_committed=0
json_report_was_committed=0
run_log_size=$(git -C "$repo_root" cat-file -s HEAD:labs/lab-04/run.log 2>/dev/null || printf '0')
[[ $run_log_size =~ ^[0-9]+$ ]] && ((run_log_size > 0)) && run_log_was_committed=1
if git -C "$repo_root" show HEAD:labs/lab-04/last_run.json 2>/dev/null |
  python3 -c '
import json
import sys
report = json.load(sys.stdin)
assert set(report) == {"mode", "selected", "succeeded", "failed", "success"}
assert report["mode"] in {"dry-run", "apply"}
assert all(isinstance(report[key], int) for key in ("selected", "succeeded", "failed"))
assert isinstance(report["success"], bool)
' >/dev/null 2>&1; then
  json_report_was_committed=1
fi

pass() {
  ((passes += 1))
  printf 'PASS: %s\n' "$1"
}

fail() {
  ((failures += 1))
  printf 'FAIL: %s\n' "$1"
}

if bash -n "$lab_dir/logmaint.sh" &&
   bash -n "$lab_dir/tests/reset_fixture.sh" &&
   bash -n "$lab_dir/tests/prediction_probes.sh" &&
   bash -n "$lab_dir/tests/run.sh"; then
  pass 'Lab 4 scripts have valid Bash syntax'
else
  fail 'Lab 4 scripts have valid Bash syntax'
fi

student_test="$lab_dir/tests/test_json_report.sh"
if [[ -f "$student_test" ]] && bash -n "$student_test" && bash "$student_test"; then
  pass 'student-authored JSON report test passes'
else
  fail 'create tests/test_json_report.sh and make its focused JSON check pass'
fi

bash "$lab_dir/tests/run.sh"
published_status=$?
if (( published_status == 0 )); then
  pass 'all published safety and behavior checks pass'
else
  fail 'all published safety and behavior checks pass'
fi

cron_complete=0
systemd_complete=0
if ! grep -q '/ABSOLUTE/PATH/TO/REPOSITORY' "$lab_dir/schedule/lab4-cron.txt"; then
  cron_complete=1
fi
if ! grep -q '/ABSOLUTE/PATH/TO/REPOSITORY' "$lab_dir/schedule/lab4-logmaint.service"; then
  systemd_complete=1
fi

if (( cron_complete + systemd_complete == 1 )); then
  pass 'exactly one scheduler template is completed'
else
  fail 'exactly one scheduler template is completed'
fi

if (( cron_complete == 1 )); then
  cron_line="$(grep -Ev '^[[:space:]]*($|#)' "$lab_dir/schedule/lab4-cron.txt" | head -n 1)"
  if [[ "$cron_line" == *'--dry-run'* && "$cron_line" == *'--days 7'* &&
        "$cron_line" != *'sudo'* ]]; then
    pass 'completed cron entry preserves the safe dry-run contract'
  else
    fail 'completed cron entry preserves the safe dry-run contract'
  fi
elif (( systemd_complete == 1 )); then
  if grep -q '^ExecStart=.*--days 7 --dry-run$' "$lab_dir/schedule/lab4-logmaint.service" &&
     grep -q '^OnActiveSec=' "$lab_dir/schedule/lab4-logmaint.timer" &&
     ! grep -q 'sudo' "$lab_dir/schedule/lab4-logmaint.service"; then
    pass 'completed systemd units preserve the safe dry-run contract'
  else
    fail 'completed systemd units preserve the safe dry-run contract'
  fi
fi

if (( run_log_was_committed == 1 )); then
  pass 'committed run log preserves timestamped summaries'
else
  fail 'commit the nonempty run.log produced by your completed tool before submission'
fi

if (( json_report_was_committed == 1 )); then
  pass 'committed last_run.json has the required typed fields'
else
  fail 'commit the valid last_run.json produced by your completed tool before submission'
fi

if [[ -s "$lab_dir/scheduler_status.txt" ]]; then
  pass 'scheduler or fallback evidence file is present'
else
  fail 'scheduler or fallback evidence file is present'
fi

if awk '
  /^[[:space:]]+[a-z0-9_]+:/ {
    value=$0
    sub(/^[^:]+:[[:space:]]*/, "", value)
    gsub(/[[:space:]"\047]/, "", value)
    if (value == "") empty=1
  }
  END {exit(empty ? 0 : 1)}
' "$lab_dir/lab_record.yml"; then
  fail 'structured response fields are complete'
else
  pass 'structured response fields are complete'
fi

printf '\nResult: %s passed; %s failed.\n' "$passes" "$failures"
(( failures == 0 ))
