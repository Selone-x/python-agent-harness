# Behavioral evaluation scenarios

These are manual/agent-host acceptance tasks, not claims of completed evaluations.
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

Run with both Codex and Claude Code before claiming host-specific behavioral
acceptance. This repository does not require an LLM API key for normal use or
automatically launch paid agent evaluations.
