# Add a project-specific lint rule

Agree the exact prohibited syntax and legitimate alternatives first. Prefer an
existing Ruff/type/import rule when it already expresses the requirement.
Do not infer runtime purity or arbitrary return types from an identifier's name.

Preserve the selected engine. For structural ast-grep rules, use its valid/invalid
fixtures and run `ast-grep test`, then scan agreed roots with `ast-grep scan`.
For Semgrep, use the installed `semgrep-rule-creator` skill when available, or
follow the same test-first acceptance with annotated ruleid/ok fixtures and actual
engine validation. A dataflow requirement needs explicit sources/sinks and an
honest statement of the installed engine's interprocedural limits.
The Fixit procedure below applies when Python CST rules are the agreed choice.

New scaffolds use `sgconfig.yml`, `lint-rules/*.yml` and YAML snippet fixtures under
`lint-fixtures/`, with reviewed diagnostics in its `__snapshots__` directory. The
static group runs both `ast-grep test --include-off` and `ast-grep scan --error src
tests`. Add aliases and syntax forms only when the rule actually handles them.

Merge configuration, rule implementations, fixtures and snapshots into the spec's
`inputs` before claiming current evidence. Include non-Python test data too; scanning
the Python test inventory does not automatically hash every external fixture.

Keep deliberately invalid source snippets out of ordinary application/test roots.
For ast-grep/Fixit prefer YAML/string snippets, so normal Python quality checks do
not parse the negative examples. Semgrep fixtures may need Python files under a
separate `lint-fixtures/semgrep/` tree: configure a reviewed, narrow exclusion for
that tree in broad Ruff/type scans when necessary. Keep normal `src` and `tests`
fully checked; do not weaken their rules or coverage for negative lint fixtures.

Add a Fixit LintRule to the target project's rule module. Its VALID examples must
exercise intended legitimate code; INVALID examples must exercise actual policy
violations, including relevant aliases and boundaries. Report the precise CST node.

Run these examples through Fixit's real engine, for example with the supported
`fixit.testing.add_lint_rule_tests_to_module(globals(), [YourRule()])` integration.
Add a check that runs the rule tests and another that lints the intended source,
test and tool roots. Configure local Fixit rule discovery in the target's existing
configuration. Keep each suppression specific and justified.

Map the specification requirement to the rule-test check and evidence test file.
Actually execute a valid sample and a deliberately invalid sample through the
configured CLI. A generated class or a successful import is not rule acceptance.

Document known static-analysis limits and the remaining review/test requirements.
Avoid importing the current trading framework or copying its domain-specific
Result/DTO rules into unrelated projects.
