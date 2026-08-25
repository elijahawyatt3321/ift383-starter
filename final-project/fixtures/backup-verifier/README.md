# Backup manifest fixture

`manifest.json` lists expected relative paths, sizes, and SHA-256 digests. `sample-tree/` is the bounded tree to verify. Paths are relative to `sample-tree/`; never read outside that directory.

The fixture contains ordinary match, missing, and changed cases. Your program must calculate them rather than rely on filenames or row positions.

For this fallback, the CLI accepts the manifest path and sample-tree path. A manifest entry is `changed` when its present file disagrees with either the recorded byte size or SHA-256 digest. The JSON result contains:

- `ok`: true only when both arrays below are empty;
- `missing`: manifest paths that are absent from the tree; and
- `changed`: present manifest paths whose size or digest differs.

Sort both path arrays. Reject an unsupported digest algorithm, malformed manifest, or path that escapes the bounded sample tree with a useful nonzero failure.
