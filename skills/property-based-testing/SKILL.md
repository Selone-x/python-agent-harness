---
name: property-based-testing
description: Write, review or debug Python property-based tests with Hypothesis using meaningful invariants, independent oracles, constrained generators and minimized counterexamples. Use for properties over an input domain, not mutation campaigns or ordinary example-only tests.
---

Find a property justified by the project's contract and input domain. Reuse its
existing property-testing library. Adding a new dependency is part of the user's
authorized testing scope only when that scope supports it; do not silently migrate
an existing suite or refactor business code as part of installing this skill.

State valid inputs, expected errors, invariants and allowed loss/normalization.
Choose a property with observable consequences:

- Roundtrip: decoding an encoded value preserves the declared information.
- Independent oracle: compare against a simpler trusted model or hand-derived rule.
- Idempotence: repeating a normalization or configuration operation changes nothing.
- Invariant: a transition preserves accounting, bounds, ownership or another contract.
- Metamorphic relation: a justified input transformation has a predictable effect.
- Algebraic law: identity, associativity or commutativity only where the contract promises it.

Prefer a property that constrains the result beyond its type or lack of crashes.
Do not duplicate the production algorithm in the expected result. Roundtrip alone
can miss mutually compensating codec defects, and sortedness alone can miss lost
elements: add independent examples or complementary invariants where needed.

Build strategies that directly generate the intended domain, with explicit boundary
values, malformed inputs when relevant and finite sizes. Avoid filtering away most
cases with `assume` or excluding the case that revealed a defect. Use Decimal and
timezone rules only when required by the target's contract.

Use the project's bounded Hypothesis profiles and normal warning/health checks.
Keep generated tests deterministic where required, isolated from live clocks,
network, global state and test order. For transitions and retries, use a small
stateful model with explicit preconditions and postconditions.

When a failure is minimized, preserve the counterexample and reproduction details.
Decide whether the property, generator or implementation violates the contract.
Add an explicit regression for a confirmed defect and rerun the targeted suite.
Do not weaken the property, health checks or domain to make the example disappear.

Read [the review and failure guide](references/review.md) for weak assertions,
vacuous generation or a failing property. If no meaningful property is justified,
report that result and use independent example tests rather than inventing a law.
Report the property, domain, oracle, profile, actual result and untested limits;
generated examples are a search for counterexamples, not a proof over all inputs.

This is a portable Python adaptation of Trail of Bits material. See [NOTICE.md](NOTICE.md)
for provenance and changes, and [LICENSE](LICENSE) for the directory's license.
