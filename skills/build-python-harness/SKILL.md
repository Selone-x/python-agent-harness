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
Use [the tool map](references/tool-workflows.md) when selecting tools or explaining
the path from a requirement to a command, artifact and acceptance condition.

Before generation, agree the project's purpose, architecture, source/test roots,
toolchain, check commands and test invariants. Inspect existing code and
configuration first. Ask only about decisions that inspection cannot establish.
Preserve existing guidelines and tooling; the new-project defaults are proposals.

Use `overview` for read-only discovery, the render preview and current evidence
when a valid specification exists. Before applying, present a plan that names:
observed mechanisms and their source files; existing tools and instructions to
preserve; proposed additions and their reasons; decisions that need user input;
the generated-file diff or a visible conflict; and verification commands. Label
agent proposals separately from observations and declared policy. Do not invent
commands, architecture, approval or evidence when the overview is incomplete.
After checks, distinguish configured commands from current successful evidence,
manual review and unverified server protection. The overview does not run doctor.

Record each requirement with an honest enforcement mode: executable check,
test, or review. Automated requirements need executed positive/negative evidence;
semantic review requirements must remain visible. Do not invent a Result model,
DTO shape, dependency direction or universal directory hierarchy.

Use the CLI to validate the specification and preview rendering before applying
it in a feature branch. Keep unrelated application changes out of adoption.
Report existing debt and a repair plan; do not lower agreed thresholds or mark
missing evidence as successful. For custom rules use
[the lint recipe](references/custom-lints.md).

Use companion skills when installed and relevant: `spec-to-code-compliance` for
an explicitly scoped requirements audit, `semgrep-rule-creator` for custom rules,
`property-based-testing` for meaningful Hypothesis properties, and `mutation-testing`
for bounded mutmut setup or result analysis. Each is a standalone folder in this
checkout's `skills` directory; do not assume it was installed with this skill.
Their presence does not authorize a full audit, mutation campaign or tool migration.
New scaffolds propose Vulture and Complexipy as required static checks; preserve
agreed existing tools on adoption. Complexipy's default cognitive limit is 15,
with no inline-ignore bypass; describe threshold changes as policy changes.
Scaffolds also enable Ruff C901 at 10 and tested ast-grep rules. Their negative
snippets are YAML outside source/tests, and all rule/config/fixture/snapshot inputs
are fingerprinted. Preserve a user-selected alternative engine during adoption.

Run the configured groups and audit. Ordinary checks must not launch deep mutation
or benchmark workloads. Respect time/output budgets and avoid RAM-backed temp trees.
An accepted render is not evidence that tests or server protections passed.

For GitHub/GitLab use [the protection guide](references/protection.md). Read actual
settings with doctor; configure external settings only within explicit user
authorization. Do not grant the coding agent bypass/admin rights as a workaround.

Return changes, commands, actual results, unmet requirements and unverified parts.
Never claim that prose, coverage or a manifest guarantees absence of bad code.
