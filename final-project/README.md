# Final Project

## Problem and user

State the bounded problem, intended user or role, and chosen self-designed or fallback brief.

## Command contract

Document one CLI entry point, one success command, one named failure command, and the keys and types in the top-level JSON object produced by the success path. Keep these consistent with `acceptance.success_behavior` and `acceptance.failure_behavior` in `PROJECT_PLAN.yml`.

## Bounded input

Identify the single non-sensitive input set committed under `final-project/fixtures/`. Explain how to restore any timestamp-dependent fixture before testing.

## Local run

Provide the exact local command and one compact input/output example.

## Tests

All three to five meaningful automated tests must run through:

```bash
bash final-project/tests/run.sh
```

## Container

Document the exact Podman build command and one runtime command that supplies input at runtime rather than baking it into the image.

## Continuous integration

Document what the final-project workflow tests and builds. Keep the workflow least-privilege boundaries supplied by the course, and retain the separate Lab 7 workflow.

## Technical path

Name the one value selected in `PROJECT_PLAN.yml` and explain in one or two sentences why it fits this problem:

- `text-pipeline` means the core is a readable chain of command-line tools with a meaningful regular expression.
- `bash-automation` means Bash implements the substantive decisions, validation, loops, or file operations.
- `python-automation` means Python implements substantive data handling, error handling, or operating-system/filesystem work.

These paths are equally valid. Select exactly one and make sure the implementation actually follows it.
