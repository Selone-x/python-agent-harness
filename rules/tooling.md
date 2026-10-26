# Tooling and change policy

Use `just setup`, `just fmt`, targeted pytest, then `just check`. Generated files,
logs and caches belong in ignored disk-backed directories. Keep uv.lock committed.

All application and policy changes use feature branches and PRs/MRs. Start each
description with a short summary of what changed, why, and the resulting behavior.
Describe validation and compatibility below it. Do not disable checks, lower
thresholds or add unexplained suppressions to get a green pipeline.

Changes to policy, CI, exclusions and thresholds need explicit separate review.
Keep requirement discovery, local validation, live platform protection and agent
behavioral evaluation distinct in reports. Do not claim protection from a
configuration file or unavailable paid platform feature.
