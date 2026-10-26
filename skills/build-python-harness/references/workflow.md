# Build and maintain a project harness

## New project

Inspect the requested destination and ancestor instructions. Agree project kind,
Python/tool choices and architecture before choosing constraints. Use `init
--scaffold` only in an empty directory. The starter package smoke test proves only
its initial version contract; it is not meaningful coverage of future features.

Edit the draft specification to reflect the agreed requirements. Source roots
must cover all production files. Libraries require artifact checks; other kinds
need packaging only if the project actually produces a distribution.

Run validate, preview render, apply, setup and checks. Commit the resulting lock
in a feature branch. Review the real diff and prepare a PR/MR with a short summary.

## Existing project

Use inspect and read pyproject/lock files, tests, instructions and CI. Do not
replace Black/mypy/Poetry simply because new-project defaults use Ruff/ty/uv.
Use init without scaffolding; it writes only the draft specification. Replace
its deliberately failing draft commands with the existing approved commands.
Agree missing coverage discovery and test oracle requirements explicitly.

Render owns files or managed instruction blocks. Never force-overwrite a conflict.
Resolve the desired combined content with the user, preserving application code
and unrelated jobs. An existing GitLab pipeline needs its local include added
without replacing stages, rules, variables or other jobs.

Run checks to expose debt. Report failures with a repair plan; do not rewrite
business behavior as part of harness installation. Missing evidence is unfinished
work, not permission to weaken a gate.

## Audit

Validate configuration, inspect requirements/evidence mappings, run audit and the
agreed check groups. Review whether assertions come from independent expected
results. Inspect current provider protection with doctor if authorized to read it.
Separate static import checking from runtime wiring and semantic review.

## Update

Use a clean feature branch, review changes to policy and runtime versions, and
preview rendering. Managed output conflicts stop the update. Keep ordinary code
changes out of policy updates. Run targeted regressions and required groups.
Provider removal or changed platform permissions needs explicit separate review.
