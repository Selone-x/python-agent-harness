# Work in this repository

Read rules/code.md, rules/architecture.md, rules/testing.md and rules/tooling.md.
Run Python commands through uv; install the locked environment with `just setup`.
Work in a feature branch. Never commit or push directly to main. Merge only
through a PR/MR whose latest commit passed required CI.

Preserve the target project's architecture and tool choices. Treat unknown
requirements as unknown, not as permission to impose this repository's defaults.
Specify inputs, outcomes and invariants before changing behavior. Add independent
regressions, run targeted tests, then `just check`. Do not weaken policy for green.

Report actual commands, outcomes, enforcement limits and checks not performed.
The public license is undecided; publication is a separate, unfinished step.

<!-- python-agent-harness:begin -->
Read `.harness/policy.md` and `.harness/project.toml`.
Run `python -I .harness/runner.pyz validate` and the configured check groups.
Keep existing guidelines. Policy/CI changes need explicit review.
<!-- python-agent-harness:end -->
