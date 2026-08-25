# Retention planner fixture

Run `bash reset_times.sh` before testing. It restores fixed UTC modification times under `data/` and never touches another directory.

Use a documented fixed cutoff such as `2026-08-01T00:00:00Z`; do not base reproducible tests on the current clock.

For this fallback, the CLI accepts the data directory and an explicit UTC cutoff. It plans only; it must not delete, compress, or rewrite a file. The JSON result contains:

- `scanned`: ordinary files inspected directly under the bounded directory;
- `eligible`: files with modification times strictly earlier than the cutoff;
- `bytes`: total bytes across eligible files; and
- `files`: eligible relative filenames in ascending order.

Do not follow symbolic links. A missing directory and an invalid cutoff are named nonzero failures; choose one of them for the project plan and tests.
