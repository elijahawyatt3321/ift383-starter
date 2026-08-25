# Final-project dependency allowlist

The project is graded offline. Keep its runtime small and reproducible.

Allowed runtime choices:

- Python standard library on either approved Python base;
- Bash and the listed command-line tools only when they are already present in the chosen approved base;
- `grep`, `sed`, `awk`, `find`, `xargs`, `sort`, `uniq`, and coreutils when already present in that base;
- Git only for development history, not as an application runtime dependency.

Allowed test dependency:

- Fedora's `python3-pytest` package when the project uses Python tests.

No other Python package, language package manager, framework, database, network client, external service, or downloaded binary is approved. Ask the instructor before committing a dependency not listed here.

Both approved images are Debian-based. Do not assume that a Fedora package is present inside the container, and do not add a networked package-install step. The full `python-bookworm` option is the safer supplied choice for a Bash-heavy project because it includes a broader command-line userland; verify every command your project actually uses.
