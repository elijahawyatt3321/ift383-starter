# Approved final-project base images

Choose exactly one immutable reference. Approximate x86_64 compressed sizes are comparison data, not grading targets.

| Option | Exact approved image | Runtime note | Approximate size |
|---|---|---|---:|
| Python slim | `docker.io/library/python:3.13.13-slim@sha256:aa938a849bcb82dce8f49480f056ab82bf5c1c3ebc294f0430f37b6820e7f286` | Python 3.13 is included | 41 MB |
| Python bookworm | `docker.io/library/python:3.13.13-bookworm@sha256:0544e35a04d3d3272a5e180a402065bfa84402bf39431a727f8989e32ffce979` | Python and a broader Debian userland are included | 365 MB |

Both values are multi-platform manifest-list digests and need no package-install step for a standard-library Python project. Do not substitute `latest`, a shortened digest, or another image.
