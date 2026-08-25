#!/usr/bin/env bash

set -u
export LC_ALL=C

# This starter contains two bounded defects. It also needs the optional status
# argument described in the assignment.
log_file='access.log'

awk '{print $1}' "$log_file" |
  sort |
  uniq -c |
  sort -k1,1n -k2,2
