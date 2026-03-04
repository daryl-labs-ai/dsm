# Governance

## Project

**DSM — Daryl Sharding Memory**: append-only, auditable memory kernel for AI agents.

## Maintainer organization

**Daryl Labs**

**Founder & CEO:** Mohamed Azizi

## Maintainers

DSM is maintained by Daryl Labs. Contributions are welcome under the terms of the [MIT License](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Kernel ownership

The kernel is the stable core of DSM. Ownership and review of kernel code are held by the maintainer organization.

**Kernel path:** `src/dsm_kernel/*`

Changes to the kernel (config, API, catalog, integrity, event log, shard manager) require maintainer review and must follow the architecture rules below.

## Decision model

- **Routine changes**: Pull requests, review by maintainers, merge when approved.
- **Architecture changes**: Require:
  - A **Pull Request** with a clear description
  - **Maintainer review** and approval
  - An **ADR (Architecture Decision Record)** document in `docs/adr/` describing the change and rationale

## Architecture rules

- **Kernel minimal**: No business logic in the kernel; stable API only.
- **Modules evolve**: Router, validator, loop, and other modules can evolve independently; the kernel does not depend on them for core behavior.
- **Derived indexes**: Catalog and integrity manifest are derived from shards and are rebuildable.

Architecture changes (e.g. new kernel responsibilities, breaking API changes) must follow the decision model above (PR, maintainer review, ADR).

## Contact

- **Security**: See [SECURITY.md](SECURITY.md).
- **Trademarks and brand**: See [TRADEMARKS.md](TRADEMARKS.md).
- **General**: Open an [issue](https://github.com/daryl-labs-ai/dsm/issues) for questions or contributions.
