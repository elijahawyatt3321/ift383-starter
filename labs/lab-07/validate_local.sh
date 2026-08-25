#!/usr/bin/env bash
set -u

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../.." && pwd)
tool_root="$repo_root/inventory-tool"
starter_workflow="$repo_root/workflow-starters/inventory-tool.yml"
active_workflow="$repo_root/.github/workflows/inventory-tool.yml"
failures=0
generated_output=$(mktemp) || {
  printf '[FAIL] Could not create a bounded output file.\n' >&2
  exit 1
}
committed_output=$(mktemp) || {
  rm -f -- "$generated_output"
  printf '[FAIL] Could not create a bounded committed-output file.\n' >&2
  exit 1
}
trap 'rm -f -- "$generated_output" "$committed_output"' EXIT
committed_output_ready=0
if git -C "$repo_root" show HEAD:labs/lab-07/container_output.txt >"$committed_output" 2>/dev/null \
  && [[ -s $committed_output ]]; then
  committed_output_ready=1
fi

pass() {
  printf '[PASS] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1" >&2
  failures=$((failures + 1))
}

printf 'Lab 7 probe observations\n'
if grep -Eq '^COPY[[:space:]]+inventory-tool/' "$tool_root/Dockerfile"; then
  printf 'observations.q1=build-fails\n'
else
  printf 'observations.q1=build-succeeds\n'
fi

workflow_for_probe=$starter_workflow
if [[ -f $active_workflow ]]; then
  workflow_for_probe=$active_workflow
fi
if grep -Eq 'working-directory:[[:space:]]*inventory-tool/tests' "$workflow_for_probe"; then
  printf 'observations.q2=tests-missed\n'
else
  printf 'observations.q2=tests-run\n'
fi
printf 'observations.q3=different-instances\n\n'

printf 'Published local validation\n'
python_base='docker.io/library/python:3.13.13-slim@sha256:aa938a849bcb82dce8f49480f056ab82bf5c1c3ebc294f0430f37b6820e7f286'
bookworm_base='docker.io/library/python:3.13.13-bookworm@sha256:0544e35a04d3d3272a5e180a402065bfa84402bf39431a727f8989e32ffce979'
if grep -Fxq "FROM $python_base" "$tool_root/Dockerfile" \
  || grep -Fxq "FROM $bookworm_base" "$tool_root/Dockerfile"; then
  pass 'Dockerfile uses one exact approved digest-pinned base.'
else
  fail 'Dockerfile must use one exact approved digest from BASE_IMAGE_COMPARISON.md.'
fi

if ! grep -Eq '^COPY[[:space:]]+inventory-tool/' "$tool_root/Dockerfile" \
  && grep -Eq '^COPY[[:space:]].*inventory\.py' "$tool_root/Dockerfile" \
  && grep -Eq '^COPY[[:space:]].*inventory_tool' "$tool_root/Dockerfile"; then
  pass 'Dockerfile copies application source from the documented build context.'
else
  fail 'Repair the Dockerfile context paths and include both runtime source locations.'
fi

for required in '.git/' '__pycache__/' '.pytest_cache/' '.venv/' 'generated/'; do
  if grep -Fxq "$required" "$tool_root/.dockerignore"; then
    pass ".dockerignore contains $required"
  else
    fail ".dockerignore is missing $required"
  fi
done

if [[ -f $active_workflow ]]; then
  pass 'Active inventory workflow exists at the documented path.'
  workflow=$active_workflow
else
  fail 'Copy the inactive starter to .github/workflows/inventory-tool.yml during Lab 7.'
  workflow=$starter_workflow
fi

permission_count=$(sed -n '/^permissions:/,/^[^[:space:]]/p' "$workflow" \
  | grep -Ec '^[[:space:]]{2}[A-Za-z0-9_-]+:')
if ((permission_count == 1)) \
  && grep -Eq 'contents:[[:space:]]*read' "$workflow" \
  && grep -Eq 'persist-credentials:[[:space:]]*false' "$workflow" \
  && ! grep -Eq 'pull_request_target|secrets\.|secrets\[|[[:space:]]+(write|write-all)|id-token:|packages:|issues:|pull-requests:' "$workflow"; then
  pass 'Workflow retains the supplied least-privilege boundaries.'
else
  fail 'Workflow least-privilege boundaries are incomplete.'
fi

uses_count=$(grep -Ec '^[[:space:]]*uses:' "$workflow")
pinned_uses_count=$(grep -Ec '^[[:space:]]*uses:[[:space:]]*[^@[:space:]]+@[0-9a-f]{40}([[:space:]]|$)' "$workflow")
if ((uses_count > 0 && uses_count == pinned_uses_count)) \
  && grep -Eq '^[[:space:]]*push:' "$workflow" \
  && grep -Eq 'branches:.*main' "$workflow" \
  && grep -Eq 'uses:[[:space:]]*actions/checkout@[0-9a-f]{40}([[:space:]]|$)' "$workflow"; then
  pass 'Workflow uses the main-branch trigger and complete checkout pin.'
else
  fail 'Workflow must run for main pushes and retain the supplied complete checkout pin.'
fi

if ! grep -Eq 'working-directory:[[:space:]]*inventory-tool/tests' "$workflow" \
  && grep -Eq 'working-directory:[[:space:]]*inventory-tool$' "$workflow" \
  && grep -Fq 'tests/test_lab6_supplied.py' "$workflow"; then
  pass 'Workflow test step uses the inventory-tool working directory and real suite.'
else
  fail 'Repair the workflow test working directory without weakening its suite.'
fi

if grep -Eq 'python3[[:space:]]+inventory\.py[[:space:]]+--help' "$workflow" \
  && grep -Eq '(docker|podman)[[:space:]]+build.*inventory-tool' "$workflow"; then
  pass 'Workflow includes the named CLI smoke check and image build.'
else
  fail 'Workflow needs a separate --help smoke check and an inventory image build.'
fi

if [[ -f $tool_root/tests/test_min_size.py && -f $tool_root/tests/test_symlink_skip.py ]]; then
  if (
    cd "$tool_root" &&
      python3 -m pytest -q \
        tests/test_lab5_supplied.py \
        tests/test_lab6_supplied.py \
        tests/test_min_size.py \
        tests/test_symlink_skip.py
  ); then
    pass 'Complete Lab 5 and Lab 6 test suites pass.'
  else
    fail 'Complete Lab 5 and Lab 6 test suites must pass before packaging.'
  fi
else
  fail 'Student-created min-size and symlink-skip tests are required.'
fi

if command -v podman >/dev/null 2>&1; then
  image=localhost/ift383-inventory:lab7
  if podman build --pull=never --network=none --tag "$image" "$tool_root"; then
    pass 'Podman image build succeeds.'
    if podman run --rm \
      --volume "$tool_root/fixtures/container-input:/input:ro,Z" \
      "$image" /input --format json >"$generated_output"; then
      if python3 -m json.tool "$generated_output" >/dev/null; then
        pass 'Mounted-input container run succeeds with valid JSON.'
        if ((committed_output_ready == 1)) \
          && cmp -s "$generated_output" "$committed_output"; then
          pass 'Committed container_output.txt matches the reproduced run.'
        else
          fail 'Run the documented container command, save container_output.txt, and commit the matching result.'
        fi
      else
        fail 'Mounted-input output must be valid JSON.'
      fi
    else
      fail 'Mounted-input container run failed.'
    fi
  else
    fail 'Podman image build failed.'
  fi
else
  fail 'Podman is unavailable; install the course-required container tools in your Fedora VM.'
fi

if grep -Eq '^[[:space:]]+[a-z0-9_]+:[[:space:]]*""([[:space:]]*#.*)?$' "$script_dir/lab_record.yml"; then
  fail 'Complete every supplied Lab 7 record field.'
else
  pass 'Lab 7 record fields are complete.'
fi

if ((failures > 0)); then
  printf '\nLocal validation: FAIL (%d issue(s))\n' "$failures" >&2
  exit 1
fi

printf '\nLocal validation: PASS\n'
