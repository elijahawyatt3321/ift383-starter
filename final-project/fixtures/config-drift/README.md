# Configuration drift fixture

`baseline.json` maps relative configuration paths to expected JSON objects. `current/` is the bounded current tree. Compare normalized parsed objects, not formatting or object-key order.

Report added, removed, and changed relative paths in deterministic ascending order.

For this fallback, the CLI accepts the baseline file and current-tree directory. A path is `changed` only when both versions exist and their parsed JSON values differ. The JSON result contains:

- `in_sync`: true only when all three arrays are empty;
- `added`: current JSON paths absent from the baseline;
- `removed`: baseline paths absent from the current tree; and
- `changed`: shared paths whose parsed values differ.

Reject a missing input or invalid JSON with a useful nonzero failure. Do not classify formatting or object-key order as drift.
