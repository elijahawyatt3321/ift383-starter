#!/usr/bin/env bash

set -u

selected_dir="${1:-.}"

if [[ ! -d "$selected_dir" ]]; then
  printf 'ERROR: directory does not exist: %s\n' "$selected_dir" >&2
  exit 2
fi

if ! selected_dir_absolute="$(cd -- "$selected_dir" && pwd -P)"; then
  printf 'ERROR: cannot enter directory: %s\n' "$selected_dir" >&2
  exit 3
fi

printf 'SYSTEM REPORT\n'

# STUDENT SLOT 1 OF 4
# Replace the next command with one that prints the absolute working directory
# using this exact label: WORKING_DIRECTORY:
printf 'WORKING_DIRECTORY: STUDENT_SLOT_1\n'

# STUDENT SLOT 2 OF 4
# Replace the next command with one that prints the kernel release using this
# exact label: KERNEL_RELEASE:
printf 'KERNEL_RELEASE: STUDENT_SLOT_2\n'

# STUDENT SLOT 3 OF 4
# Replace the next command with one that prints the non-hidden entry count for
# "$selected_dir_absolute" using this exact label: ENTRY_COUNT:
printf 'ENTRY_COUNT: STUDENT_SLOT_3\n'

printf 'TOP_MEMORY_PROCESSES:\n'
# STUDENT SLOT 4 OF 4
# Replace the next command with a pipeline that prints the PID, %%MEM, and
# command columns for the three processes using the most memory.
printf 'STUDENT_SLOT_4\n'

# INDEPENDENT TRANSFER
# Add exactly one new labeled report field below this comment, following the
# choices and evidence directions in the assignment.
