# Select and execute a tool workflow

Start with `inspect` and the existing project's actual config/commands. Its
`tools`/`tool_evidence` fields describe dependencies and configuration, not installed
binaries, active enforcement or passing results. New-project defaults are proposals.

| Workflow | Purpose and acceptance |
| --- | --- |
| `just setup` | Install agreed dependencies and pre-commit; no campaign or service startup |
| `just fmt` | Apply formatter and safe lint fixes; review the diff |
| pre-commit | Run the bounded static group, including rule tests; no behavior/deep workloads |
| `just check` | Validate, run all required spec groups and require current successful gate evidence |
| targeted pytest | Reproduce behavior with the configured workspace temp root and active Hypothesis profile |
| `just deep` | Explicitly run configured API/mutation/benchmark checks under the total deep budget |
| `mutation-gate` | Read complete mutmut results with time/output bounds and apply strict all-killed acceptance |

Ruff covers formatting, common mistakes and cyclomatic complexity; ty covers types;
Vulture finds high-confidence unused code; Complexipy estimates cognitive complexity.
The defaults for new projects are cyclomatic 10 and cognitive 15, scanning source
and tests. Preserve an existing project's chosen metric and thresholds on adoption.

For project syntax policy, prefer an existing rule; otherwise choose ast-grep,
Fixit or Semgrep according to what must be expressed and the project's existing
engine. ast-grep's starter rule is intentionally limited to direct qualified calls.
Fixit is available for Python CST policies, not an automatically enabled global
policy. The runtime itself checks declared import boundaries transitively; no
external import-linter installation is required for that graph.

For behavior, use the property-based-testing skill to select an independent oracle
and generator, then pytest/Hypothesis to execute it. For API schemas, add Schemathesis
only after agreeing an isolated service, schema and lifecycle. For assertion
sensitivity, use the mutation-testing skill and the complete engine-plus-acceptance
profile; a tool's zero exit alone is not acceptance.

For semantic requirements, the spec-to-code-compliance skill traces authoritative
text to actual paths and evidence. Keep those requirements as review unless an
executable check truly expresses them. A visible `review` finding is not proof of
a completed independent review or a reason to claim a semantic CI guarantee.

Add all configs, rules, snapshots, non-Python test fixtures and acceptance adapters
that affect results to the existing spec's `inputs`, merging rather than replacing
the array. Execute the real positive and negative examples, then the configured
scan and required groups. Preserve bounds on commands and temporary data; command
log limits do not provide arbitrary workload disk/memory quotas.
