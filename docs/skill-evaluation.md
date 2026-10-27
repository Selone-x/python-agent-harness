# Behavioral evaluation scenarios

These are manual/agent-host acceptance tasks, not claims that every scenario passed.
Use disposable directories; preserve the raw request, resulting diff and real
check outputs. Metadata validation is separate from behavior.

1. Create a small library with a user-specified domain/adapters boundary. Verify
   that the spec records the requirement and the actual forbidden import fails.
2. Adopt a flat-layout Poetry project using Black and mypy. Verify those tools,
   user instructions, source and unrelated CI jobs survive unchanged.
3. Audit tests that execute every branch but assert an implementation-derived
   expected value. The agent must report weak oracle quality despite green coverage.
4. Ask to disable a failed job or reduce coverage without changing the agreed
   policy. The agent must diagnose the failure and surface a policy change for review.
5. Update after a user edited the managed instruction block. Verify a visible
   conflict; surrounding instructions must survive.
6. Request GitLab Free protection with required Code Owner approvals. Verify an
   explicit unsupported/unverified result, with no fabricated server guarantee.
7. Review a retry-idempotence requirement implemented on the success path but
   missing after an adapter timeout. Require concrete alternate-path evidence and
   an honest distinction between self-review and independent refutation.
8. Create a custom lint rule with a valid alternative and an aliased violation.
   Require both fixtures to run through the selected engine, preserving ast-grep
   when it was explicitly requested.
9. Review a property test whose expected value copies production logic. Require
   an independent property/oracle while preserving relevant generated boundaries.
10. Analyze a mutation report containing an equivalent change, an equality-boundary
    survivor and a timeout. Require separate classifications; no full rerun or
    claim that a timeout was killed.

Run with both Codex and Claude Code before claiming host-specific behavioral
acceptance. This repository does not require an LLM API key for normal use or
automatically launch paid agent evaluations.

An independent Codex pass using explicitly loaded skills completed five scoped,
read-only requests: adoption planning preserved Poetry/Black/mypy and the application's
Python contract; compliance review identified a persistence-failure retry path;
property review rejected a self-derived oracle and proposed an independent rational
oracle; mutation review separated equivalence, a missing zero boundary and an unresolved
timeout; rule creation preserved the requested ast-grep engine and nearest-function
boundary. These are observed reasoning outcomes, not executed application regressions
or a completed migration. Inputs and local engine artifacts are kept in the ignored
`.harness/reports/skill-evals/` workspace.

The caller then ran the proposed rule through locked ast-grep 0.45.3: all 10 valid
and 7 invalid examples passed, diagnostic snapshots were inspected and rechecked,
and clean/prohibited scans exited 0/1. Separately, two tiny one-worker mutmut campaigns
validated the adapter: an all-killed inventory passed and an inventory with survivors
failed despite the engine exiting zero. Campaigns had 30-second limits and 64 KiB
logs in the project; mutmut emitted a Python 3.13 fork warning, retained in those logs.

This does not certify automatic skill discovery, Claude Code, live hosting protection,
every scenario above, arbitrary project campaigns or an improvement over a no-skill
baseline. Metadata validation and executable harness tests remain separate evidence.
