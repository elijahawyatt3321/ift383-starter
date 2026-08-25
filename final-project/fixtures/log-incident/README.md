# Log incident fixture

`events.log` is a bounded, non-sensitive input using six whitespace-separated fields:

```text
timestamp host severity service code message
```

Treat severity and code as exact fields. Do not search the entire line when the contract names one field.

For this fallback, the CLI accepts the log path and one severity to match. The JSON result contains:

- `total_records`: all valid input records;
- `matched_count`: records whose severity field exactly matches the requested value; and
- `severity_counts`: counts for every severity found in the file.

Sort object keys deterministically. A missing file and a malformed record are named nonzero failures; choose one of them for the project plan and tests.
