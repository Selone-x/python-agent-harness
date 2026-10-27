# Contributing

Help make Python Agent Harness useful in real projects. A small reproduction of
an adoption problem, a tested custom rule or a clearer skill workflow can be as
valuable as a runtime feature.

The original-code license is still pending, as described in the
[release status](README.md#status-and-license). Contribution licensing is also
unfinished. The adapted third-party skills retain their own licenses and notices.

## Find your starting point

| Area | Where to look | Useful contributions |
| --- | --- | --- |
| Runtime | [src/python_agent_harness](src/python_agent_harness) | Configuration, discovery, generation, evidence validation and bounded commands |
| Agent workflows | [skills](skills) | Focused instructions supported by realistic observed cases |
| Project rules | [lint-rules](lint-rules), [lint-fixtures](lint-fixtures) | Engine-tested rules with matching and nonmatching examples |
| Regressions | [tests](tests) | Independent expectations, failure paths and integration cases |
| Documentation | [README](README.md), [usage](docs/usage.md), [specification](docs/specification.md) | Reproducible examples and clear explanations of actual behavior |

Before a larger change, describe the problem, a concrete example and the behavior
you want. For a bug, include the command, relevant versions, expected and actual
results, and a minimal sanitized configuration. Keep credentials and private
application data out of reports.

## Work locally

Requires Python 3.13+, uv and just on Linux or macOS. Read [AGENTS.md](AGENTS.md)
and the linked rules before editing.

```sh
git switch -c feat/describe-your-change
just setup
```

Run Python commands through uv. For behavior changes, establish inputs, expected
results and invariants, then add a regression based on an independent oracle.
Run the relevant tests first; for example, when changing the command runner:

```sh
uv run --locked pytest tests/test_runner.py --no-cov
just fmt
just check
```

`just check` validates the specification, runs required groups through the bounded
runner and checks their current evidence. It includes formatting, linting, types,
Vulture, complexity, ast-grep, tests, coverage and packaging. Pre-commit runs the
static group. Keep temporary files and logs in the ignored project directories.

If a change affects generated artifacts, preview and review them before applying:

```sh
uv run --locked harness render
uv run --locked harness render --apply
just check
```

A skill metadata check validates structure. A meaningful behavioral evaluation
needs a realistic request and observable outcomes; see the
[evaluation guide](docs/skill-evaluation.md). New custom rules need positive and
negative cases executed through the chosen engine. Keep optional mutation/API
workloads narrow and explicitly budgeted; normal checks do not start full campaigns.

## Open a focused pull request

Use a feature branch and a PR/MR. Never commit or push directly to `main`; merge
only after required CI passes for the latest commit.

Start the description with a brief summary of **what changed, why, and the resulting
behavior**. Include the actual validation commands and outcomes, compatibility
considerations and anything left unverified. A before/after example helps when the
trigger is subtle.

Preserve the target project's tool choices during adoption. Describe policy, CI,
threshold and exclusion changes separately for review. Fix the cause of a failed
check; keep the agreed checks and test expectations intact.
