# CLAUDE.md Upkeep

Applies to the repo's own CLAUDE.md. Never touch a parent-directory CLAUDE.md
shared across projects (e.g. ~/github_projs/CLAUDE.md).

Before each commit, check the staged diff. Default: no edit.
Edit CLAUDE.md only if the diff changes build/run/test commands, dependencies,
config/env, module layout/architecture, or makes an existing entry wrong.

- Smallest change: fix or delete the affected line. Never append history.
- Skip refactors, bug fixes, tests, docs-only, and anything derivable from code.
- Stage the edit in the same commit. Report "CLAUDE.md: no change" or the line changed.
- Soft limit: ~200 lines. If over, trim stale or derivable entries first.
- No CLAUDE.md? Ask before creating one.
