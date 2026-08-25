# Approved Lab 7 base images

Choose one exact digest below. The digest, not the mutable tag, determines the image content. Approximate compressed sizes are for the x86_64 variant and are comparison data, not grading targets.

| Decision token | Exact approved image | Python availability | Package manager | Approximate compressed size | Operational tradeoff |
|---|---|---|---|---:|---|
| `python-slim` | `docker.io/library/python:3.13.13-slim@sha256:aa938a849bcb82dce8f49480f056ab82bf5c1c3ebc294f0430f37b6820e7f286` | Python 3.13 included | `apt` | 41 MB | Smaller and contains the runtime needed by this standard-library tool |
| `python-bookworm` | `docker.io/library/python:3.13.13-bookworm@sha256:0544e35a04d3d3272a5e180a402065bfa84402bf39431a727f8989e32ffce979` | Python 3.13 included | `apt` | 365 MB | Includes a much broader Debian userland that this tool does not need |

Both references are multi-platform manifest-list digests and already contain Python. Do not shorten a digest, replace it with `latest`, or add an unapproved base. No package-install step or third-party runtime package is required for the inventory tool.
