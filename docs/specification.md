# Project specification v1

`.harness/project.toml` is a reviewed input, not an LLM configuration.
Unknown keys are rejected. Start with `harness init` and edit the draft with your
agent before rendering. Commit it alongside generated output and the lockfile.

Required fields: `schema_version = 1`, distribution `name`, project `kind`
(`library`, `service`, `cli`, `research`), harness runner `python`, nonempty
`sources` and `tests` arrays, and selected `providers` (`github`, `gitlab`).
Paths are relative to the project; absolute paths and escapes are rejected.
Multiple source roots and a flat package layout are supported.
Use `inputs` for extra files/directories that affect checks (for example custom
lint implementations and fixtures); they participate in report fingerprints.
Explicit requirement evidence also participates. Repository-wide `.` roots are
rejected to avoid scanning environments, caches and unrelated code.

`setup` is an array of argv arrays, executed only by the explicit setup command.
It should install the agreed toolchain and project dependencies from locked inputs.

```toml
[[checks]]
id = "lint"
group = "static"
argv = ["poetry", "run", "ruff", "check", "."]
timeout = 60
```

Groups `static` and `tests` are required. Libraries also require `package`.
`deep` is optional and excluded from ordinary CI/check invocations. Every command
within a selected group is mandatory. `@python` is the runner interpreter;
`@harness` invokes the project's isolated bundled runtime. Other argv values are
literal arguments; shell expansion is never performed.

`quality` accepts `lines`, `branches`, `coverage`, `output_limit` and `deep_budget`.
Percentages use exact decimal arithmetic; defaults are 97 and 100. Budgets are
positive integers. The test command must produce fresh coverage.py JSON at the
declared path, with every production file included. Configure coverage source
discovery explicitly; relying only on imported modules is insufficient.

```toml
[[boundaries]]
source = "example.domain"
forbidden = ["example.adapters", "requests"]

[[requirements]]
id = "domain-isolation"
description = "Domain code depends on contracts and stdlib only"
enforcement = "check"
check = "architecture-examples"
evidence = ["tests/test_architecture_examples.py"]
```

The referenced check must exist and execute the positive/negative examples;
the evidence path must exist. A requirement with `enforcement = "test"` follows
the same mapping rules. Use `enforcement = "review"` for semantic requirements
that cannot honestly be automated. Requirement ids and check ids are unique.

The import graph follows static local imports transitively. Dynamic imports,
dependency injection, plugin loading and business correctness need separate
evidence. A matched directory name is not proof that the architecture is correct.

Custom Fixit rules live in the consumer project, are covered by real engine
tests and are mapped to an explicit check. See the skill's
[custom lint recipe](../skills/build-python-harness/references/custom-lints.md).

Run `render` to preview paths and sizes, then review actual changed files after
`render --apply`. `render --check` returns nonzero on drift. The ownership manifest
tracks generated files and only the managed portions of instruction files.
Unowned file conflicts and edited managed blocks stop rendering. Disabling an
existing provider requires a separate manual removal review.
