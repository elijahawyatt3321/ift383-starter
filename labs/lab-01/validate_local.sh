#!/usr/bin/env bash

set -u

lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
scratch_dir="$(mktemp -d)" || {
  printf 'ERROR: could not create a bounded validation directory.\n' >&2
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

if bash -n "$lab_dir/sysreport.sh" && bash -n "$lab_dir/broken_greeting.sh"; then
  pass 'Lab 1 scripts have valid Bash syntax'
else
  fail 'Lab 1 scripts have valid Bash syntax'
fi

first_line="$(sed -n '1p' "$lab_dir/broken_greeting.sh")"
if [[ -x "$lab_dir/broken_greeting.sh" && "$first_line" == '#!/usr/bin/env bash' ]] &&
   "$lab_dir/broken_greeting.sh" > "$scratch_dir/greeting.out" 2> "$scratch_dir/greeting.err"; then
  pass 'greeting script has repaired launch requirements'
else
  fail 'greeting script has repaired launch requirements'
fi

max_count="$(grep -Ec '^max_connections=200$' "$lab_dir/server.conf")"
debug_active="$(grep -Ec '^[[:space:]]*debug=' "$lab_dir/server.conf")"
debug_commented="$(grep -Ec '^[[:space:]]*#[[:space:]]*debug=' "$lab_dir/server.conf")"
log_count="$(grep -Ec '^log_path=/var/log/app\.log$' "$lab_dir/server.conf")"
last_setting="$(awk '!/^[[:space:]]*($|#)/ {line=$0} END {print line}' "$lab_dir/server.conf")"
if (( max_count == 1 && debug_active == 0 && debug_commented == 1 && log_count == 1 )) &&
   [[ "$last_setting" == 'log_path=/var/log/app.log' ]]; then
  pass 'server configuration contains the three precise edits'
else
  fail 'server configuration contains the three precise edits'
fi

if grep -q 'STUDENT_SLOT_' "$lab_dir/sysreport.sh"; then
  fail 'all four base report slots are completed'
else
  pass 'all four base report slots are completed'
fi

mkdir -p "$scratch_dir/directory with spaces"
printf 'one\n' > "$scratch_dir/directory with spaces/alpha.txt"
printf 'two\n' > "$scratch_dir/directory with spaces/beta.txt"
printf 'hidden\n' > "$scratch_dir/directory with spaces/.hidden.txt"

(
  cd -- "$lab_dir" || exit 1
  ./sysreport.sh "$scratch_dir/directory with spaces"
) > "$scratch_dir/report.out" 2> "$scratch_dir/report.err"
report_status=$?

expected_kernel="$(uname -r)"
if (( report_status == 0 )) &&
   grep -Fxq "WORKING_DIRECTORY: $lab_dir" "$scratch_dir/report.out" &&
   grep -Fxq "KERNEL_RELEASE: $expected_kernel" "$scratch_dir/report.out" &&
   grep -Fxq 'ENTRY_COUNT: 2' "$scratch_dir/report.out"; then
  pass 'base report values work for a spaced directory'
else
  fail 'base report values work for a spaced directory'
fi

awk '
  /^TOP_MEMORY_PROCESSES:$/ {capture=1; next}
  capture && lines < 4 {print; lines++}
' "$scratch_dir/report.out" > "$scratch_dir/processes.out"
if [[ "$(wc -l < "$scratch_dir/processes.out" | tr -d ' ')" == '4' ]] &&
   sed -n '1p' "$scratch_dir/processes.out" | grep -Eq 'PID.*%MEM.*(COMMAND|CMD)' &&
   tail -n 3 "$scratch_dir/processes.out" |
     awk 'NF >= 3 && $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+([.][0-9]+)?$/ {ok++} END {exit(ok == 3 ? 0 : 1)}'; then
  pass 'memory section contains its header and three process rows'
else
  fail 'memory section contains its header and three process rows'
fi

(
  cd -- "$lab_dir" || exit 1
  ./sysreport.sh
) > "$scratch_dir/no-argument.out" 2> "$scratch_dir/no-argument.err"
no_argument_status=$?
(
  cd -- "$lab_dir" || exit 1
  ./sysreport.sh /etc
) > "$scratch_dir/etc.out" 2> "$scratch_dir/etc.err"
etc_status=$?
(
  cd -- "$lab_dir" || exit 1
  ./sysreport.sh "$scratch_dir/missing"
) > "$scratch_dir/missing.out" 2> "$scratch_dir/missing.err"
missing_status=$?
if (( no_argument_status == 0 && etc_status == 0 && missing_status != 0 )); then
  pass 'required argument cases return appropriate statuses'
else
  fail 'required argument cases return appropriate statuses'
fi

if [[ -s "$lab_dir/sysreport_output.txt" ]] &&
   grep -q '^WORKING_DIRECTORY:' "$lab_dir/sysreport_output.txt" &&
   grep -q '^KERNEL_RELEASE:' "$lab_dir/sysreport_output.txt" &&
   grep -q '^ENTRY_COUNT:' "$lab_dir/sysreport_output.txt" &&
   grep -q '^TOP_MEMORY_PROCESSES:$' "$lab_dir/sysreport_output.txt"; then
  pass 'saved no-argument report contains all base sections'
else
  fail 'saved no-argument report contains all base sections'
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

if grep -Eq '^  field:[[:space:]]*"?(uptime|root_disk|memory|logged_in_users)"?[[:space:]]*$' "$lab_dir/lab_record.yml"; then
  pass 'independent field choice uses one published option'
else
  fail 'independent field choice uses one published option'
fi

printf '\nResult: %s passed; %s failed.\n' "$passes" "$failures"
(( failures == 0 ))
