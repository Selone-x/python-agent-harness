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

## Rebuild the README animations

The main setup diagram is an illustrated workflow authored with the external
[animdiagram skill](https://github.com/praveenvijayan/animdiagram). Its editable
source is `assets/readme-tailored.svg`; `assets/readme-tailored.spec.json` holds the
ten-second motion sequence. The light version is derived from the dark source;
the static version keeps the light diagram's nodes, connectors and labels while
removing its motion layers. The README selects that static file for reduced-motion
readers. Attribution is in `assets/readme-tailored-NOTICE.txt`.

Keep the skill checkout outside this project. With a local checkout, recompile
the motion and derive the light version using the existing locked environment:

```sh
uv run --locked python /path/to/animdiagram/scripts/timeline.py assets/readme-tailored.spec.json --inject assets/readme-tailored.svg
uv run --locked python /path/to/animdiagram/scripts/skin.py assets/readme-tailored.svg --to light
uv run --locked python /path/to/animdiagram/scripts/check.py assets/readme-tailored.svg assets/readme-tailored-light.svg --strict
```

After geometry or copy changes, update the static companion as well. Inspect the
animation in an `<img>` element, both color schemes and reduced-motion mode, then
run `just check`. This diagram illustrates the agreed setup flow; it does not
establish agent-host acceptance or a guarantee about application correctness.

The GIFs are narrated replays of a verified isolated example, with summarized
terminal output. The fee test expects `100 - 7 == 93`; the incorrect source returns
107, and correcting the source passes the same tests. The installation sequence
was also exercised in an isolated checkout, including the initial scaffold checks.
These examples do not certify arbitrary project requirements.

The expandable customization demo shows an illustrated user/agent exchange.
Its resulting import boundary, forbidden-import failure, corrected audit and full
project checks were exercised with real CLI commands while preserving the existing
tool configuration. The agent dialogue and installation prompt are explanatory
scenes, not recordings of a particular agent host.

To change the GIFs or their captions, edit the scene definitions and SVG rendering in
[tools/render_readme_media.py](tools/render_readme_media.py), then run:

```sh
uv run --locked python tools/render_readme_media.py
```

Rendering requires `rsvg-convert` and `ffmpeg` on PATH. It installs no environments,
runs sequentially with bounded logs/timeouts, keeps frames in `.harness/reports/`
and uses one ffmpeg thread. Review both static SVG posters and representative
frames of each GIF. Verify any changed commands or outcome claims against real
execution before updating the scenes, then run `just check`.
The generator participates in static checks, and tools/assets are explicit report
inputs so changes invalidate earlier evidence.
