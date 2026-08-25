#!/usr/bin/env bash

set -u

sample_path='/bounded/fixture/old api.log'
set -- $sample_path
unquoted_argument_count=$#
set -- "$sample_path"
quoted_argument_count=$#

printf 'Unquoted path argument count: %s\n' "$unquoted_argument_count"
printf 'Quoted path argument count: %s\n' "$quoted_argument_count"
if (( unquoted_argument_count == 1 )); then
  printf 'OBSERVATION q1=one-path\n'
else
  printf 'OBSERVATION q1=split-path\n'
fi

simulated_processing_failure() {
  return 7
}

simulated_processing_failure
failure_status=$?
printf 'Simulated processing failure status: %s\n' "$failure_status"
if (( failure_status == 0 )); then
  printf 'OBSERVATION q2=yes\n'
else
  printf 'OBSERVATION q2=no\n'
fi
