# Add a project-specific Fixit rule

Agree the exact prohibited syntax and legitimate alternatives first. Prefer an
existing Ruff/type/import rule when it already expresses the requirement.
Do not infer runtime purity or arbitrary return types from an identifier's name.

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
