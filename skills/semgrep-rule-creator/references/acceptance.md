# Accept a custom static rule

Use the selected engine's own fixture format. For Semgrep, from the project root:

```sh
uv run --locked semgrep --validate --config lint-rules/no-blocking-sleep.yaml
uv run --locked semgrep --test --config lint-rules/no-blocking-sleep.yaml lint-fixtures/semgrep/no-blocking-sleep.py
uv run --locked semgrep --error --config lint-rules/no-blocking-sleep.yaml src tests
```

These commands assume Semgrep is in the target's locked environment and the named
files are the agreed rule/fixtures. Add the existing dependency-group flag if needed.
If the engine is unavailable, report validation as blocked; do not claim that the
examples passed. Installing the skill does not install Semgrep or enable a ruleset.

For a no-blocking-sleep policy, distinguish `time.sleep` inside an async function
from the permitted synchronous context and `await asyncio.sleep`. Include the
import aliases and nested functions that the rule promises to support. Record
unsupported forms explicitly instead of broadening the pattern to every call.

For ast-grep, use YAML `valid`/`invalid` fixtures and `ast-grep test`, followed by
`ast-grep scan` against the intended roots. Check its installed version and error
severity configuration: a displayed finding alone does not prove a nonzero exit.
See [the official test guide](https://ast-grep.github.io/guide/test-rule.html).

Before marking enforcement as active, deliberately scan one prohibited example
through the configured command and observe its nonzero exit, then observe a clean
example pass. Keep that experiment in a disposable directory, not in application
source. A fixture test alone does not prove that CI scans the right roots.

Merge the actual configuration, rule, fixture and snapshot paths into the spec's
`inputs` array before accepting a report. Existing `inputs` must be preserved.
New scaffolds already list `lint-rules`, `lint-fixtures` and `sgconfig.yml`.

Use YAML valid/invalid snippets for ast-grep so normal Python linters/type checks
do not treat intentional violations as application code. Keep reviewed snapshots
and run `ast-grep test --include-off`; generate/update snapshots only during a
reviewed rule change, never automatically in CI. For Semgrep's Python fixtures,
keep the separate tree above out of application tests/coverage and configure only
a narrowly reviewed fixture exclusion in broad Ruff/type scans when necessary.
Never exclude the normal source/test roots to accommodate a negative example.
