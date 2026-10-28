# Usage and operating limits

Detailed setup, tool behavior and evidence limits for Python Agent Harness.
Start with the [quick start](../README.md#quick-start) for a first project.
Run constructor commands from its checkout unless a different directory is shown.

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
`just check` invokes the specification's bounded groups and aggregate gate, using
the same checks as CI. Pre-commit runs only their static group. Use `just fmt` to
apply formatting; checks never silently format the project. The standalone stdlib
runner is a bootstrap exception to using uv for installed Python tools.

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

## Dead code and API contracts

Vulture is a required static check in this repository and every new scaffold.
Run it alone with `just dead-code`. It scans source and tests together at confidence
80, matching the framework's existing policy. Dynamic use can require a narrowly
reviewed whitelist; do not lower confidence or ignore entire trees for a green run.

Complexipy is also required in `just check` and the static CI group. Run it alone
with `just complexity`. It checks source and tests with an inclusive cognitive
complexity limit of 15, without inline-ignore bypasses. This complements existing
cyclomatic checks rather than replacing their metric. Caches stay in the ignored
report directory; changing thresholds or exclusions is a reviewed policy change.

The scaffold's Ruff C901 limit is 10, alongside Complexipy 15. Hypothesis profiles
are shared with the constructor: dev 50/25, ci 200/50, nightly 1000/200
(examples/stateful steps), a 200 ms deadline and enabled health checks. pytest's
configured temporary root and retention apply to direct targeted runs as well.

ast-grep is a required static check here and in new scaffolds. `sgconfig.yml`
loads `lint-rules/`; `lint-fixtures/` contains valid/invalid YAML snippets and
reviewed diagnostic snapshots. Both fixture tests and source scans run in static.
The starter no-shell-command rule covers direct `subprocess.run`/`Popen` calls
with literal `shell=True`; it does not resolve aliases or prove runtime purity.
These paths are explicit fingerprint inputs. Fixit remains the tested library for
opt-in Python CST rules; import architecture uses the runtime's own transitive
graph checker. There is no unused import-linter dependency. Semgrep is an alternative
for agreed dataflow rules and is not installed by the skill alone.

New scaffolds also include an optional, separately locked `api` dependency group
with Schemathesis and `.harness/api-check.example.toml`. After agreeing an API's
schema and isolated test target, copy that check into `.harness/project.toml`,
replace the schema/URL and add schema/config/hooks to the specification's `inputs`.
Start the service separately, then run `just deep`. Missing schema, unavailable
service, nonzero exit and timeout fail the configured check.

The example uses one worker, examples/fuzzing phases, 25 generated examples per
operation, a five-second request timeout and a 120-second outer process limit.
It retains shrinking, uses deterministic generation and disables the example
database. The runner bounds command output; no service or campaign is started
by installing the dependency group. Ordinary checks exclude `deep`.

To make API contracts mandatory on every MR, move that configured check to the
`tests` group and arrange service startup in the corresponding CI job. All checks
in the group must pass. Stateful API tests need a separate agreed lifecycle and
budget. Schemathesis checks the declared API schema; business invariants still
need independent tests. The constructor itself has no HTTP API: its small real-engine
tests generate requests against an in-process WSGI fixture and reject an invalid
response without a network server. These tests run in the ordinary test job.

Existing-project adoption preserves current dependencies and check commands;
adding either tool there remains an explicit configuration decision.

## Mutation acceptance

The optional `mutation` dependency group locks mutmut 3.7.0. New scaffolds include
`.harness/mutation-check.example.toml`: a one-worker engine command limited to
60 seconds, followed by `@harness mutation-gate`. Configure narrow source paths,
selected tests, dependency/cache invalidation and a passing baseline before copying
those checks into the spec. Add non-Python rule/test inputs explicitly. `just deep`
executes the configured optional group; neither normal checks nor pre-commit run it.

`mutation-gate` reads `mutmut results --all true` through a bounded 30-second command.
Its strict preset requires a nonempty, unique, well-formed inventory of only killed
mutants. Survivors, unknown statuses, timeouts, missing tests, skipped/untested rows
and command failures cannot pass. It never generates or applies mutations. To use
another environment, pass the literal results command after `--`:

```sh
uv run --locked harness mutation-gate -- poetry run mutmut results --all true
```

This verifies the observed inventory, not freshness of an independently copied
cache. Use the complete deep profile, `on_dependency_change = "rerun"`, declared
inputs and current source/test evidence. Equivalent mutants require separate
reviewed policy; this strict preset does not silently exempt them. Time/output
budgets do not impose a universal memory or disk quota on arbitrary project code.

## Adopt an existing project

Run `overview` first to inspect the existing project without changing it:

```sh
uv run --locked harness --root /path/to/project overview
```

The JSON includes discovered tool declarations and their sources, lockfiles,
instructions, CI paths and common command files. Discovery is not exhaustive:
it does not parse command files or infer that tools are installed or used.
When a valid specification exists, it also includes declared checks, requirements,
the actual render diff or a conflict, and required-group gate findings. It separates
missing, stale, failed and malformed group reports; a failed group does not imply
every individual requirement in that group failed. Missing, invalid or stale
evidence does not become a successful result. The command does
not execute checks or contact the hosting provider; server protection is unverified
until an explicit `doctor` query. Optional `deep` checks are not covered by the
required gate. A missing specification is reported as missing; an invalid one
or a blocked render preview retains inspection facts and exits 2.

Ask your agent to distinguish observations, proposals and unresolved decisions,
and to map existing project mechanisms before proposing additions. The overview
does not itself decide what to preserve or approve changes on the user's behalf.
`inspect` remains available for discovery alone. Then run `init` **without** `--scaffold`; only the draft
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

See [the specification reference](specification.md). The specification is
the source of truth for generated instructions and CI, with explicit mappings
from requirements to checks, evidence files or human review.

See the [tool workflow guide](../skills/build-python-harness/references/tool-workflows.md)
for the roles of tools and skills, acceptance commands and their limits.

Coverage requires a complete inventory, even for modules never imported by
tests. Lines and branches use separate exact comparisons. A program without
branches can pass; missing tests or an empty coverage report cannot.

Static import boundaries include transitive local imports and the existing package
initializers executed by those imports or by loading the checked module. Dynamic
imports, framework injection and runtime wiring require tests/review. A useful
assertion oracle cannot be established by the presence of a test filename or a high
coverage percentage. Mutation and benchmark commands can be added to the deep
group; project-specific performance baselines and mutation policies require agreement.

Reports are bound to the policy, runtime, production source, tests, dependency
metadata and actual managed artifact contents. Editing or deleting a generated
workflow, hook, policy file or managed instruction block invalidates earlier
reports. User text outside managed instruction blocks is excluded unless the
whole file is explicitly declared in `inputs`. Stale reports, skipped groups,
nonzero exits, timeouts and excessive output fail. Each command runs without a
shell, sequentially, in a process group;
logs are bounded. Commands in an approved spec still execute arbitrary project
code: this tool is not a sandbox for malicious code.

## Install the skills

The pack contains six self-contained skills:

| Skill | Purpose |
| --- | --- |
| [build-python-harness](../skills/build-python-harness/SKILL.md) | Build or adopt the executable harness |
| [disciplined-code-change](../skills/disciplined-code-change/SKILL.md) | Implement and verify behavioral changes incrementally |
| [spec-to-code-compliance](../skills/spec-to-code-compliance/SKILL.md) | Trace requirements to implementation and test evidence |
| [semgrep-rule-creator](../skills/semgrep-rule-creator/SKILL.md) | Create custom rules and validate matches/nonmatches |
| [property-based-testing](../skills/property-based-testing/SKILL.md) | Design and review meaningful Hypothesis properties |
| [mutation-testing](../skills/mutation-testing/SKILL.md) | Configure bounded mutmut campaigns and analyze survivors |

Copy each selected skill directory, including references and any NOTICE/LICENSE,
into the agent's skill directory:

- Codex: `~/.agents/skills/` or the project's `.agents/skills/`.
- Claude Code: `~/.claude/skills/` or the project's `.claude/skills/`.

Ask your agent to use `build-python-harness`, describing the project and desired
architecture. The skill uses this local checkout via `uv run --project /path/to/python-agent-harness harness ...`.
Other agents can use the same instructions and CLI; host discovery and behavior
have not been certified for every agent. See [skill evaluation scenarios](skill-evaluation.md).

## GitHub and GitLab

Both generators preserve unrelated jobs. GitHub has a required `harness-gate`
job with `always()` and strict report validation. GitLab uses reserved `.pre`
and `.post` stages to avoid replacing a project's stages. Jobs are not allowed
to fail, and artifacts expire after seven days.

Generating YAML does not configure server protection. Follow
[the protection guide](../skills/build-python-harness/references/protection.md), then verify actual settings:

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


See the [release and license status](../README.md#status-and-license) before publication.
