# Template Library

Reusable building blocks that container packages consume. Each subdirectory targets a specific concern:
- `docker/`: Dockerfile fragments and helper scripts copied or referenced by package builds.
- `scripts/`: Shell helpers sourced by top-level scripts (e.g., logging, retry logic).
- `tests/`: Shared smoke or integration helpers used across packages.

Keep templates dependency-free and idempotent. If a package needs something bespoke, consider upstreaming it here so other packages benefit.
