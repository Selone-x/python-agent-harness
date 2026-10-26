---
name: build-python-harness
description: Build, adopt, audit or update an executable quality harness for a Python project from its own architecture and guidelines. Use for harness/tooling work, not ordinary feature implementation or unsolicited refactoring.
---

Use the user's existing agent and a local checkout of Python Agent Harness.
Locate that checkout from the invocation context; do not invent an installation
path or assume a published package. Run its CLI as
`uv run --project <checkout> harness --root <target> <command>`.

Establish the requested mode: new project, adoption, audit or update. Read only
the relevant parts of [the workflow](references/workflow.md).

Before generation, agree the project's purpose, architecture, source/test roots,
toolchain, check commands and test invariants. Inspect existing code and
configuration first. Ask only about decisions that inspection cannot establish.
Preserve existing guidelines and tooling; the new-project defaults are proposals.

Record each requirement with an honest enforcement mode: executable check,
test, or review. Automated requirements need executed positive/negative evidence;
semantic review requirements must remain visible. Do not invent a Result model,
DTO shape, dependency direction or universal directory hierarchy.

Use the CLI to validate the specification and preview rendering before applying
it in a feature branch. Keep unrelated application changes out of adoption.
Report existing debt and a repair plan; do not lower agreed thresholds or mark
missing evidence as successful. For custom rules use
[the lint recipe](references/custom-lints.md).

Run the configured groups and audit. Ordinary checks must not launch deep mutation
or benchmark workloads. Respect time/output budgets and avoid RAM-backed temp trees.
An accepted render is not evidence that tests or server protections passed.

For GitHub/GitLab use [the protection guide](references/protection.md). Read actual
settings with doctor; configure external settings only within explicit user
authorization. Do not grant the coding agent bypass/admin rights as a workaround.

Return changes, commands, actual results, unmet requirements and unverified parts.
Never claim that prose, coverage or a manifest guarantees absence of bad code.
