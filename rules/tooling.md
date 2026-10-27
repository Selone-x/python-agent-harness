# Tooling and change policy

Use `just setup`, `just fmt`, targeted pytest, then `just check`. Generated files,
logs and caches belong in ignored disk-backed directories. Keep uv.lock committed.

`just check` and CI run the same specification groups through the bounded runner;
the gate requires their current reports. Pre-commit runs the same static group,
including formatting, types and rule fixtures, and never launches the tests/deep
groups. Use standalone Python only for the stdlib runner bootstrap; installed
Python tools run through uv. Report logs are bounded, not arbitrary workload files.

All application and policy changes use feature branches and PRs/MRs. Start each
description with a short summary of what changed, why, and the resulting behavior.
Describe validation and compatibility below it. Do not disable checks, lower
thresholds or add unexplained suppressions to get a green pipeline.

Changes to policy, CI, exclusions and thresholds need explicit separate review.
Keep requirement discovery, local validation, live platform protection and agent
behavioral evaluation distinct in reports. Do not claim protection from a
configuration file or unavailable paid platform feature.
