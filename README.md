# Python Agent Harness

Build an executable quality harness from a Python project's own requirements.
Use your existing coding agent: no model API key or hosted service is required.

The agent agrees the architecture and guidelines with you. The CLI validates the
specification, previews generated files, runs bounded checks, and reports what
was actually verified. It does not decide your business contracts or silently
rewrite an existing application to satisfy a generic architecture.

## Local development

Requires Python 3.13+, uv and just on Linux or macOS. Process-group and output
limits use POSIX primitives; Windows execution is not supported in this version.

```sh
just setup
uv run harness --help
just check
```

The runtime has no third-party dependencies. Development dependencies are locked
in `uv.lock`. Tests and command logs use disk-backed workspace directories.

## Create a new project

Create an empty destination directory, then run from this repository:

```sh
uv run harness --root /path/to/new-project init \
  --name example-project --package example_project --kind library \
  --provider github --provider gitlab --scaffold
uv run harness --root /path/to/new-project inspect
```

Agree the description, requirements, source/test roots, check commands and
dependency boundaries in `.harness/project.toml`. `python` is the harness runner
version, not a request to migrate an existing application's Python version.
The initial package/version test is only a packaging smoke test.

```sh
uv run harness --root /path/to/new-project validate
uv run harness --root /path/to/new-project render
uv run harness --root /path/to/new-project render --apply
```

In the generated project, initialize Git with `git init -b feat/bootstrap` if
it is a new repository, then run `just setup`. Commit the generated `uv.lock` in a
feature branch, then `just check`. Setup resolves dependencies locally; CI uses
the committed lock and refuses to silently change it.

Each generated project carries `.harness/runner.pyz`, a reproducible bundle of
the stdlib-only runtime. It works without publishing this tool to PyPI:

```sh
python3 -I .harness/runner.pyz validate
python3 -I .harness/runner.pyz check --group static
python3 -I .harness/runner.pyz check --group tests
python3 -I .harness/runner.pyz gate
```

Library projects also require the package group. Service, CLI and research
projects do not inherit a wheel requirement. Every configured command within a
required group must succeed. The optional `deep` group runs only when explicitly
requested and has a total time budget.

## Adopt an existing project

Run `inspect` first. Then run `init` **without** `--scaffold`; only the draft
specification is created. Adoption drafts deliberately fail until the agent and
user replace the draft commands with the project's real formatter, type checker,
test runner, coverage command and setup commands. Existing Black/mypy/Poetry or
other tooling is not replaced with the defaults used by new projects.

Keep the existing architecture and commands. Adjust source roots for flat,
namespace or multiple-package layouts. Do not automatically lower coverage
requirements to the currently achieved result. Report debt and plan its repair
as a separate task.

Rendering owns only declared output files and managed instruction blocks.
It preserves surrounding `AGENTS.md`/`CLAUDE.md` content and refuses to overwrite
edited generated files or conflicting workflows. Existing GitLab jobs remain
untouched: add `local: .harness/gitlab-ci.yml` to their existing include structure
and matching merge-request workflow/job rules directly in the root configuration.
The audit reports that integration as incomplete until the include is present.

## Specification and evidence

See [the specification reference](docs/specification.md). The specification is
the source of truth for generated instructions and CI, with explicit mappings
from requirements to checks, evidence files or human review.

Coverage requires a complete inventory, even for modules never imported by
tests. Lines and branches use separate exact comparisons. A program without
branches can pass; missing tests or an empty coverage report cannot.

Static import boundaries include transitive local imports. Dynamic imports,
framework injection and runtime wiring require tests/review. A useful assertion
oracle cannot be established by the presence of a test filename or a high
coverage percentage. Mutation and benchmark commands can be added to the deep
group; no general performance baseline or mutation acceptance is invented.

Reports are bound to the policy, runtime, production source, tests and dependency
metadata. Stale reports, skipped groups, nonzero exits, timeouts and excessive
output fail. Each command runs without a shell, sequentially, in a process group;
logs are bounded. Commands in an approved spec still execute arbitrary project
code: this tool is not a sandbox for malicious code.

## Install the skill

The self-contained skill is [skills/build-python-harness](skills/build-python-harness/SKILL.md).
Copy that directory, with its references, to one of:

- Codex: `~/.agents/skills/build-python-harness` or the project's `.agents/skills/`.
- Claude Code: `~/.claude/skills/build-python-harness` or the project's `.claude/skills/`.

Ask your agent to use `build-python-harness`, describing the project and desired
architecture. The skill uses this local checkout via `uv run --project /path/to/python-agent-harness harness ...`.
Other agents can use the same instructions and CLI; host discovery and behavior
have not been certified for every agent. See [skill evaluation scenarios](docs/skill-evaluation.md).

## GitHub and GitLab

Both generators preserve unrelated jobs. GitHub has a required `harness-gate`
job with `always()` and strict report validation. GitLab uses reserved `.pre`
and `.post` stages to avoid replacing a project's stages. Jobs are not allowed
to fail, and artifacts expire after seven days.

Generating YAML does not configure server protection. Follow
[the protection guide](skills/build-python-harness/references/protection.md), then verify actual settings:

```sh
uv run harness --root /path/to/project doctor --provider github --repository owner/repo
uv run harness --root /path/to/project doctor --provider gitlab --repository group/project
```

Doctor uses the user's authenticated `gh`/`glab` CLI in read-only mode. Unavailable
settings and protections are reported as blocked. It does not store credentials
or modify server settings. GitLab required approvals depend on the tier.

A repository-local manifest detects accidental drift; it is not an independent
trust authority. An agent able to edit CI, regenerate policy and approve its own
changes can bypass repository-local controls. Separate credentials and protected
review of policy/CI are necessary for stronger enforcement.

## Current release status

The project is being prepared locally for an open-source release. The license
has intentionally **not** been selected. Do not publish a release, redistribute
derived code under an assumed license, or describe licensing as completed.
Live provider tests and behavioral runs in each agent host must be recorded
separately from local unit/integration tests.
