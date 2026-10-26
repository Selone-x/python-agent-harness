# python-agent-harness: harness policy

Project-specific harness construction with explicit enforcement limits and no hosted service.

Requirements:
- strict-specification [test]: Reject misspelled policy, unbound checks and escaping paths.
- bounded-commands [test]: Observe real exits and stop timeouts/output floods without leaving workers.
- preserve-user-content [test]: Refuse unowned conflicts and preserve instructions outside managed blocks.
- custom-lint-engine [test]: Run positive and negative project-rule examples through real Fixit.
- independent-oracle [review]: Review test expectations against documented contracts and literal boundary examples.

Coverage: lines >= 97%; branches >= 100%.
Source inventory: src/python_agent_harness

Static imports are checked transitively. Runtime wiring requires tests/review.
Evidence paths establish traceability, not assertion quality.
Mutation and benchmarks run only in the explicitly configured bounded deep group.

Do not commit or push directly to the main branch. Use a PR/MR with a short summary.
Do not weaken checks, suppressions, thresholds or expected values for green.
Policy/CI changes need separate review. Verify actual platform protection.
Use independent expected values and test relevant errors, boundaries and invariants.
