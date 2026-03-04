# Contributing

## Branching strategy

- Work on feature branches: `feature/<short-name>` (e.g. `feature/docs-readme-quickstart`).
- Base branch for new work is typically `main` or the latest merged migration branch.
- No direct commits to `main`; use pull requests.

## PR size guideline

- Keep PRs small and focused: one concern per PR (e.g. one doc section, one module change).
- Prefer several small PRs over one large refactor, especially for the kernel.

## Tests required

- New or changed behavior should be covered by tests in `tests/` (e.g. `tests/kernel/`, `tests/modules/`).
- Before submitting: run `python -m py_compile` on changed Python files and `pytest -q` from the repo root.
- Kernel and API changes must not break existing tests.

## Kernel rules

- **No change to kernel behavior** for documentation-only or repo-hygiene PRs.
- **Stable API**: existing `DSMKernel` method signatures and semantics are stable; new optional methods are allowed.
- **Derived indexes**: catalog and integrity manifest are rebuildable; do not add kernel logic that depends on them for core append/query.
- **Paths**: use `DSMConfig` (no hardcoded absolute paths) for index, catalog, manifest, event log.
