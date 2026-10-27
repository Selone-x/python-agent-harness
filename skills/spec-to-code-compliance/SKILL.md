---
name: spec-to-code-compliance
description: Compare Python implementation behavior with authoritative specifications or contracts, tracing individual requirements to code and tests and reporting evidenced divergences. Use for a requested compliance review, not general bug hunting or inventing requirements from code.
---

Compare intended behavior with what the code enforces. Preserve the user's review
scope and existing architecture; an audit request does not authorize fixing code,
rewriting the specification or changing CI acceptance.

Identify the authoritative documents, their versions and the code revision.
Distinguish mandatory behavior, recommendations and roadmap items. If intended
behavior is undocumented or contradictory, report that uncertainty rather than
deriving a specification from the implementation being checked.

Split the scoped text into individually checkable requirements. For each, state
the relevant inputs, expected outcome, invariant and any exceptions. Trace the
actual entry point, enforcement, callees, callers, error paths and alternate paths.
Read the code behind promising function names. Record searches when claiming
that enforcement is absent; include decorators, adapters and caller guards.

Inspect relevant tests and their expected-value oracle. A named test, existing
evidence file or high coverage does not establish the requirement. Execute only
the tests appropriate to the requested scope, with the project's normal budgets.
Preserve the difference between inspecting a test and observing its result.

Use these verdicts:

- `implemented`: the scoped paths enforce the stated requirement.
- `partial`: some applicable paths or cases fail to enforce it.
- `contradicted`: observed implementation behavior conflicts with the requirement.
- `stronger-than-spec`: the implementation imposes an undocumented restriction.
- `absent`: documented searches found no enforcement of the applicable requirement.
- `undecidable`: ambiguity or unavailable evidence prevents a supported verdict.

Also perform the reverse pass: inspect material behavior that the documents do not
describe. Separate implementation defects, stale documentation and uncertain intent;
rank consequences for this project rather than capitalization of MUST/SHOULD.

Challenge each proposed divergence against the specification and all relevant code
paths. Use an independent reviewer only when available and authorized. Otherwise
identify the second pass as self-review and leave independent refutation unverified.
Do not assume Claude plugin commands, other skills or delegated agents are installed.
Work in bounded requirement batches; identify unfinished requirements explicitly.

Report the scope, requirement verdicts, concrete document/code locations, searches,
observed tests and remaining uncertainty. Use [the evidence format](references/evidence.md)
when producing a saved report or judging whether an absence/partial verdict is justified.
Keep report artifacts in the project's ignored report directory unless requested otherwise.

For a harness, record semantic requirements as review unless an actual executable
check expresses them. Do not turn this agent review into a fabricated deterministic
CI guarantee or silently rewrite requirements to match current behavior.

This is a portable adaptation of Trail of Bits material. See [NOTICE.md](NOTICE.md)
for provenance and changes, and [LICENSE](LICENSE) for the directory's license.
