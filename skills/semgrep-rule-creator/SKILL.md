---
name: semgrep-rule-creator
description: Create and validate custom Semgrep rules with violating and legitimate examples run through the actual engine. Use for requested bug-pattern, security or coding-policy rules, including taint rules; preserve an explicitly requested alternative engine.
---

Establish the exact prohibited behavior, language, intended source roots and
legitimate alternatives before writing a rule. Preserve existing project tooling.
For an explicitly requested ast-grep rule, follow the same test-first discipline
using that engine's valid/invalid fixtures; do not substitute Semgrep automatically.

Read the official documentation relevant to the chosen mode:
[rule syntax](https://semgrep.dev/docs/writing-rules/rule-syntax),
[patterns](https://semgrep.dev/docs/writing-rules/pattern-syntax),
[rule tests](https://semgrep.dev/docs/writing-rules/testing-rules) and, for dataflow,
[taint analysis](https://semgrep.dev/docs/writing-rules/data-flow/taint-mode/overview).
Check the installed engine/version and its actual command options. Use the target's
locked environment; Python tool commands run through uv in uv-based projects.

Write test fixtures first, with expected matches and nonmatches from the agreed
policy. Cover direct violations, safe alternatives, relevant aliases/import forms,
nested syntax and boundary cases. Test a sanitizer's actual contract before treating
it as safe. An arbitrary function called `sanitize` is not evidence of sanitization.

Inspect how the engine represents the important syntax, then implement the smallest
rule that distinguishes those cases. Use structural patterns for structural policy;
use taint mode when the question is whether a defined source reaches a defined sink.
Name sanitizers and propagation assumptions explicitly. Semgrep CE dataflow is
intraprocedural; do not claim whole-project tracing from a local pattern test.

Run the fixtures through the real engine and validate the rule configuration. Fix
both missed violations and false positives; optimize only after the contract cases
pass, and rerun after changing patterns. Do not conceal failing cases with future-test
annotations or introduce generic patterns merely to obtain a match.

For Semgrep keep a focused YAML rule and annotated language fixture together. Use
`ruleid` for expected violations and `ok` for legitimate cases. Read
[the acceptance procedure](references/acceptance.md) when testing or wiring the rule
into a harness. A generated YAML file or successful import is unfinished acceptance.

Report the detection scope, actual engine/version/commands, passed and failed cases,
remaining analysis limits and untested forms. For a harness, configure both rule tests
and scanning of the intended project roots; associate the requirement with executed
evidence. Do not claim transitively pure code or complete alias resolution unless
the configured engine actually establishes it.

Complete the integration: merge all rule/config/fixture/snapshot paths into the
harness specification's `inputs`. Keep negative snippets separate from Python
source/tests and explain narrowly reviewed fixture exclusions where required.
The acceptance reference gives layouts for both engines; do not copy its rule
paths into a project without configuring the actual engine and source roots.

This is a portable adaptation of Trail of Bits material. See [NOTICE.md](NOTICE.md)
for provenance and changes, and [LICENSE](LICENSE) for the directory's license.
