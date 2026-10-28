---
name: disciplined-code-change
description: Implement a behavior change or fix with a test-first, incremental workflow and evidence-based refactoring. Use for code changes where observable behavior or invariants matter, not for routine prose or formatting edits.
---

Start with the user's outcome and the target repository's existing contracts,
architecture, tooling and contribution rules. Identify the behavior, relevant
boundaries and what an observer can verify; do not invent missing domain rules.
For a bug, reproduce the reported failure and identify its cause before changing
the implementation. If two attempts fail for the same reason, investigate the
shared assumption before trying another variation.

When an honest automated test is practical and warranted, write an independent
behavioral example first and observe it fail for the expected reason. Implement
the smallest coherent change and run that test again. Preserve relevant failure
and boundary cases. Do not write a weak or redundant test just to claim TDD; when
an automated test is inappropriate, explain the alternative evidence and its limit.

Work in verifiable increments. Choose data representations and boundary validation
that make invalid states harder to express, without imposing a new architecture on
the project. Keep each decision in one authoritative place. When the design is
under strain, consider how it would accommodate the requirement from the outset;
deliver the smallest coherent change within the approved scope. Consider idempotency
and recovery after interruption where operations may be retried; isolate mutable
state where concurrent writers would matter.
Remove unnecessary complexity when it is within the approved scope. Preserve
observable behavior when refactoring and run the relevant existing checks.
For genuinely repeated or error-prone work, validate one example before automating
it, then check that the automation reproduces the example.

Use the project's agreed complexity, duplication and mutation tools where they
are configured and relevant. A duplicate candidate needs semantic review; coverage
and a complexity score do not establish assertion quality. Mutation timeouts,
unrun tests and execution failures remain unresolved, not successful outcomes.
Never install tools, alter thresholds, run an unbounded campaign or change CI just
because this skill mentions a metric. Inspect actual commands, budgets and outputs.
For a requested evaluation of CRAP or structural duplication, read the
[tool notes](references/quality-tools.md); their presence does not configure a gate.

Keep track of actions, decisions and their reasons during the task; report the
relevant change, evidence from commands actually run and what remains unverified.
Keep context focused on the current decision and retain information needed for
later verification. Preserve the repository's branch, review and delivery rules.
Do not commit, push, delete a worktree or perform other external actions unless authorized.

This workflow is an independent formulation inspired by
[ub-mode](https://github.com/unclebob/ub-mode).
