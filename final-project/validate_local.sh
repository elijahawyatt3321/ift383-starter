#!/usr/bin/env bash
set -u

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$project_root/.." && pwd)
log="$project_root/local_validation.txt"

if [[ ${IFT383_FINAL_VALIDATION_CAPTURE:-0} != 1 ]]; then
  log_existed=0
  committed_log_size=$(git -C "$repo_root" cat-file -s HEAD:final-project/local_validation.txt 2>/dev/null || printf '0')
  [[ $committed_log_size =~ ^[0-9]+$ ]] && ((committed_log_size > 0)) && log_existed=1
  IFT383_FINAL_VALIDATION_CAPTURE=1 bash "$0" 2>&1 | tee "$log"
  validation_status=${PIPESTATUS[0]}
  if ((log_existed == 0)); then
    printf '[FAIL] local_validation.txt was generated. Commit it, then rerun validation.\n' >&2
    exit 1
  fi
  exit "$validation_status"
fi

failures=0
pass() { printf '[PASS] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; failures=$((failures + 1)); }

printf 'Final-project local validation\n'

plan=$project_root/PROJECT_PLAN.yml
plan_ready=1
brief_count=$(grep -Ec '^brief:' "$plan")
brief_shape_count=$(grep -Ec '^brief:[[:space:]]*"[^"]+"[[:space:]]*(#.*)?$' "$plan")
brief_value=$(sed -n 's/^brief:[[:space:]]*"\([^"]*\)".*$/\1/p' "$plan")
if ((brief_count == 1 && brief_shape_count == 1)) \
  && [[ $brief_value == self-designed \
    || $brief_value == 'Log incident summary' \
    || $brief_value == 'Backup manifest verifier' \
    || $brief_value == 'Configuration drift checker' \
    || $brief_value == 'Retention planner' ]]; then
  pass 'PROJECT_PLAN.yml selects one published brief value.'
else
  fail 'PROJECT_PLAN.yml brief must be self-designed or one exact published fallback name.'
  plan_ready=0
fi
for key in problem user_or_role command input output success_path failure_case out_of_scope; do
  if ! grep -Eq "^${key}:[[:space:]]*\"[^\"]+\"" "$plan"; then
    fail "PROJECT_PLAN.yml needs a concise value for $key."
    plan_ready=0
  fi
done
technical_path_count=$(grep -Ec '^technical_path:' "$plan")
technical_path_shape_count=$(grep -Ec '^technical_path:[[:space:]]*"[^"]+"[[:space:]]*(#.*)?$' "$plan")
technical_path_value=$(sed -n 's/^technical_path:[[:space:]]*"\([^"]*\)".*$/\1/p' "$plan")
if ((technical_path_count == 1 && technical_path_shape_count == 1)) \
  && [[ $technical_path_value == text-pipeline \
    || $technical_path_value == bash-automation \
    || $technical_path_value == python-automation ]]; then
  pass 'PROJECT_PLAN.yml selects one published technical path.'
else
  fail 'PROJECT_PLAN.yml technical_path must be exactly text-pipeline, bash-automation, or python-automation.'
  plan_ready=0
fi
for behavior in success_behavior failure_behavior; do
  if ! grep -Eq "^[[:space:]]{2}${behavior}:[[:space:]]*\"[^\"]+\"" "$plan"; then
    fail "PROJECT_PLAN.yml needs an observable acceptance.$behavior value."
    plan_ready=0
  fi
done
if ((plan_ready)); then
  pass 'PROJECT_PLAN.yml contains the bounded project contract.'
fi

source_count=0
while IFS= read -r -d '' source_file; do
  if [[ $source_file == *.py || $source_file == *.sh ]]; then
    source_count=$((source_count + 1))
    continue
  fi
  first_line=$(head -n 1 -- "$source_file" 2>/dev/null || true)
  if [[ $first_line == '#!'* ]] \
    && [[ $first_line =~ [Pp][Yy][Tt][Hh][Oo][Nn] \
      || $first_line =~ [Bb][Aa][Ss][Hh] ]]; then
    source_count=$((source_count + 1))
  fi
done < <(find "$project_root/src" -maxdepth 2 -type f -print0 2>/dev/null)
if ((source_count >= 1)); then
  pass 'Project source directory contains an implementation file.'
else
  fail 'Add the project implementation under final-project/src/.'
fi

if bash "$project_root/tests/run.sh"; then
  pass 'Published project test entry point passes.'
else
  fail 'Project test entry point must run all three to five tests successfully.'
fi

python_base='docker.io/library/python:3.13.13-slim@sha256:aa938a849bcb82dce8f49480f056ab82bf5c1c3ebc294f0430f37b6820e7f286'
bookworm_base='docker.io/library/python:3.13.13-bookworm@sha256:0544e35a04d3d3272a5e180a402065bfa84402bf39431a727f8989e32ffce979'
if grep -Fxq "FROM $python_base" "$project_root/Dockerfile" \
  || grep -Fxq "FROM $bookworm_base" "$project_root/Dockerfile"; then
  pass 'Dockerfile uses one exact approved digest.'
  pinned_base=1
else
  fail 'Dockerfile must use one exact approved digest from BASE_IMAGE_OPTIONS.md.'
  pinned_base=0
fi

if grep -Eq '^[[:space:]]*podman[[:space:]]+build' "$project_root/README.md" \
  && grep -Eq '^[[:space:]]*podman[[:space:]]+run' "$project_root/README.md"; then
  pass 'README provides exact Podman build and run commands.'
else
  fail 'README needs exact Podman build and run command lines.'
fi

workflow=$repo_root/.github/workflows/final-project.yml
if [[ -f $workflow ]]; then
  pass 'Active final-project workflow exists at the documented path.'
  permission_count=$(sed -n '/^permissions:/,/^[^[:space:]]/p' "$workflow" \
    | grep -Ec '^[[:space:]]{2}[A-Za-z0-9_-]+:')
  uses_count=$(grep -Ec '^[[:space:]]*uses:' "$workflow")
  pinned_uses_count=$(grep -Ec '^[[:space:]]*uses:[[:space:]]*[^@[:space:]]+@[0-9a-f]{40}([[:space:]]|$)' "$workflow")
  if ((permission_count == 1)) \
    && ((uses_count > 0 && uses_count == pinned_uses_count)) \
    && grep -Eq 'contents:[[:space:]]*read' "$workflow" \
    && grep -Eq 'persist-credentials:[[:space:]]*false' "$workflow" \
    && grep -Eq '^[[:space:]]*push:' "$workflow" \
    && grep -Eq 'branches:.*main' "$workflow" \
    && grep -Fq 'bash final-project/tests/run.sh' "$workflow" \
    && grep -Eq 'uses:[[:space:]]*actions/checkout@[0-9a-f]{40}([[:space:]]|$)' "$workflow" \
    && grep -Eq '(docker|podman)[[:space:]]+build.*final-project/Dockerfile' "$workflow" \
    && ! grep -Eq 'pull_request_target|secrets\.|secrets\[|[[:space:]]+(write|write-all)|id-token:|packages:|issues:|pull-requests:' "$workflow"; then
    pass 'Workflow trigger, tests, and least-privilege boundaries are ready.'
  else
    fail 'Complete the final workflow trigger, test command, and supplied safety boundaries.'
  fi
else
  fail 'Copy workflow-starters/final-project.yml to .github/workflows/ when the project begins.'
fi

if ((pinned_base)); then
  if command -v podman >/dev/null 2>&1; then
    if podman build --pull=never --network=none --tag localhost/ift383-final:local \
      --file "$project_root/Dockerfile" "$repo_root"; then
      pass 'Project image builds from the repository context without a network pull.'
    else
      fail 'Project image build failed; preload the approved base separately if needed.'
    fi
  else
    fail 'Podman is unavailable on this machine.'
  fi
fi

if ((failures > 0)); then
  printf 'Final-project local validation: FAIL (%d issue(s))\n' "$failures"
  exit 1
fi

printf 'Final-project local validation: PASS\n'
