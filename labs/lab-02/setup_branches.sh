#!/usr/bin/env bash

set -u

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  fail 'run this script inside the course Git repository'
cd -- "$repo_root" || fail 'could not enter the repository root'

current_branch="$(git branch --show-current)"
[[ "$current_branch" == 'main' ]] ||
  fail 'switch to main before running the branch setup'

[[ -z "$(git status --porcelain)" ]] ||
  fail 'commit or restore current changes before running the branch setup'

for branch in lab2/operations lab2/security; do
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    fail "branch already exists: $branch (the setup is designed to run once)"
  fi
done

config='labs/lab-02/conflict-exercise/service.conf'
[[ -f "$config" ]] || fail "missing starter file: $config"
grep -qx 'log_level=info' "$config" || fail 'starter log_level is not intact'
grep -qx 'metrics_enabled=false' "$config" || fail 'starter metrics setting is not intact'
grep -qx 'audit_enabled=false' "$config" || fail 'starter audit setting is not intact'

base_commit="$(git rev-parse HEAD)"

replace_setting() {
  local key="$1"
  local value="$2"
  local replacement_file="${config}.replacement.$$"

  if ! awk -F= -v key="$key" -v value="$value" '
    $1 == key {print key "=" value; next}
    {print}
  ' "$config" > "$replacement_file"; then
    rm -f -- "$replacement_file"
    fail "could not update $key"
  fi
  mv -- "$replacement_file" "$config" || fail "could not replace $config"
}

return_to_main() {
  git switch main >/dev/null 2>&1 || true
}
trap return_to_main EXIT

git switch -c lab2/operations "$base_commit" >/dev/null ||
  fail 'could not create lab2/operations'
replace_setting log_level warning
replace_setting metrics_enabled true
git add -- "$config"
git commit -m 'lab2 setup: operations configuration' >/dev/null ||
  fail 'could not commit the operations branch'

git switch main >/dev/null || fail 'could not return to main'
git switch -c lab2/security "$base_commit" >/dev/null ||
  fail 'could not create lab2/security'
replace_setting log_level error
replace_setting audit_enabled true
git add -- "$config"
git commit -m 'lab2 setup: security configuration' >/dev/null ||
  fail 'could not commit the security branch'

git switch main >/dev/null || fail 'could not return to main'
trap - EXIT

printf 'Created local branches from shared base %s:\n' "$base_commit"
printf '  lab2/operations\n'
printf '  lab2/security\n'
printf 'Current branch: %s\n' "$(git branch --show-current)"
printf 'No remote operations were performed.\n'
