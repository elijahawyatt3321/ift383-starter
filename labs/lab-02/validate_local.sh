#!/usr/bin/env bash

set -u

lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(git -C "$lab_dir" rev-parse --show-toplevel 2>/dev/null)" || {
  printf 'FAIL: Lab 2 validation must run inside the course Git repository.\n' >&2
  exit 1
}

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

if bash -n "$lab_dir/setup_branches.sh"; then
  pass 'branch setup script has valid Bash syntax'
else
  fail 'branch setup script has valid Bash syntax'
fi

current_branch="$(git -C "$repo_root" branch --show-current)"
if [[ "$current_branch" == 'main' ]]; then
  pass 'current branch is main'
else
  fail 'current branch is main'
fi

if [[ -z "$(git -C "$repo_root" status --porcelain)" ]]; then
  pass 'committed working tree is clean'
else
  fail 'committed working tree is clean'
fi

config="$lab_dir/conflict-exercise/service.conf"
if ! grep -Eq '^(<<<<<<<|=======|>>>>>>>)' "$config" &&
   grep -qx 'metrics_enabled=true' "$config" &&
   grep -qx 'audit_enabled=true' "$config" &&
   grep -Eq '^log_level=(warning|error)$' "$config"; then
  pass 'service conflict is resolved with both independent changes'
else
  fail 'service conflict is resolved with both independent changes'
fi

reason_line="$(grep -E '^  reason_code:' "$lab_dir/lab_record.yml" | head -n 1)"
if { [[ "$reason_line" =~ operations-visibility ]] && grep -qx 'log_level=warning' "$config"; } ||
   { [[ "$reason_line" =~ security-sensitivity ]] && grep -qx 'log_level=error' "$config"; }; then
  pass 'recorded reason code agrees with the resolved setting'
else
  fail 'recorded reason code agrees with the resolved setting'
fi

if grep -Eiq '^#{1,6}[[:space:]]+Running course checks[[:space:]]*$' "$repo_root/README.md"; then
  pass 'README contains the required course-check section'
else
  fail 'README contains the required course-check section'
fi

ignore_ok=1
for rule in \
  '.ift383-submissions/' \
  '.submission-evidence/' \
  '__pycache__/' \
  '*.py[cod]' \
  '.pytest_cache/' \
  '.venv/' \
  '*.tmp' \
  'inventory-tool/generated/'; do
  grep -Fxq "$rule" "$repo_root/.gitignore" || ignore_ok=0
done
if (( ignore_ok == 1 )); then
  pass 'Git ignore file preserves starter rules and adds workspace rules'
else
  fail 'Git ignore file preserves starter rules and adds workspace rules'
fi

find_two_parent_merge_affecting() {
  local relative_path="$1"
  local commit
  while IFS= read -r commit; do
    if ! git -C "$repo_root" diff --quiet "${commit}^1" "$commit" -- "$relative_path"; then
      printf '%s\n' "$commit"
      return 0
    fi
  done < <(git -C "$repo_root" rev-list --min-parents=2 --max-parents=2 main)
  return 1
}

conflict_merge="$(find_two_parent_merge_affecting labs/lab-02/conflict-exercise/service.conf)"
readme_merge="$(find_two_parent_merge_affecting README.md)"

two_parent_commit() {
  local commit="$1"
  [[ -n "$commit" ]] || return 1
  [[ "$(git -C "$repo_root" rev-list --parents -n 1 "$commit" | awk '{print NF - 1}')" == '2' ]]
}

if two_parent_commit "$conflict_merge"; then
  pass 'conflict-resolution change is preserved in a two-parent merge'
else
  fail 'conflict-resolution change is preserved in a two-parent merge'
fi

if two_parent_commit "$readme_merge"; then
  pass 'README feature is preserved in a two-parent merge'
else
  fail 'README feature is preserved in a two-parent merge'
fi

required_shas_present=1
committed_evidence=$(mktemp) || {
  printf 'FAIL: Could not create a bounded evidence-check file.\n' >&2
  exit 1
}
trap 'rm -f -- "$committed_evidence"' EXIT
if git -C "$repo_root" show HEAD:labs/lab-02/git_evidence.txt >"$committed_evidence" 2>/dev/null \
   && [[ -s "$committed_evidence" ]]; then
  for merge in "$conflict_merge" "$readme_merge"; do
    if [[ -z "$merge" ]]; then
      required_shas_present=0
      continue
    fi
    for required_sha in $(git -C "$repo_root" rev-list --parents -n 1 "$merge"); do
      grep -Fq "$required_sha" "$committed_evidence" || required_shas_present=0
    done
  done
else
  required_shas_present=0
fi
if (( required_shas_present == 1 )); then
  pass 'committed Git evidence contains both required merges and all four parents'
else
  fail 'commit Git evidence containing both required merges and all four parents'
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
