"""Independent counterexamples for package imports, suppressions and stale evidence."""

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from python_agent_harness.audit import architecture, fingerprint, suppressions
from python_agent_harness.config import load
from python_agent_harness.model import Boundary, Check
from python_agent_harness.paths import HarnessError
from python_agent_harness.render import BEGIN, apply, plan
from python_agent_harness.runner import gate, run_group


@pytest.mark.parametrize(
    "statement",
    [
        "import acme.helpers.pure",
        "import acme.helpers.pure as helper",
        "from acme.helpers.pure import value",
        "from .helpers.pure import value",
        "from .helpers import pure",
    ],
)
def test_imported_package_initializers_are_transitive_dependencies(
    project: Path, statement: str
) -> None:
    package = project / "src/acme"
    helper = package / "helpers"
    helper.mkdir()
    (package / "domain.py").write_text(statement + "\n")
    (helper / "__init__.py").write_text(
        "raise AssertionError('audit must not execute user code')\nimport sqlite3\n"
    )
    (helper / "pure.py").write_text("value = 1\n")
    spec = replace(
        load(project), boundaries=(Boundary(source="acme.domain", forbidden=("sqlite3",)),)
    )

    assert [(item.code, item.message) for item in architecture(project, spec)] == [
        ("architecture.import", "acme.domain depends on forbidden sqlite3")
    ]


def test_module_depends_on_its_own_package_initializers(project: Path) -> None:
    package = project / "src/acme"
    (package / "__init__.py").write_text("import sqlite3\n")
    (package / "domain.py").write_text("value = 1\n")
    spec = replace(
        load(project), boundaries=(Boundary(source="acme.domain", forbidden=("sqlite3",)),)
    )

    assert [item.message for item in architecture(project, spec)] == [
        "acme.domain depends on forbidden sqlite3"
    ]


def test_namespace_parents_do_not_hide_nested_initializers(project: Path) -> None:
    package = project / "src/acme"
    nested = package / "namespace/nested"
    nested.mkdir(parents=True)
    (package / "domain.py").write_text("import acme.namespace.nested.pure\n")
    (nested / "__init__.py").write_text("import sqlite3\n")
    (nested / "pure.py").write_text("value = 1\n")
    spec = replace(
        load(project), boundaries=(Boundary(source="acme.domain", forbidden=("sqlite3",)),)
    )

    assert [item.message for item in architecture(project, spec)] == [
        "acme.domain depends on forbidden sqlite3"
    ]


def test_importing_a_sibling_does_not_execute_an_unrelated_initializer(project: Path) -> None:
    package = project / "src/acme"
    helper = package / "helpers"
    helper.mkdir()
    (helper / "__init__.py").write_text("import sqlite3\n")
    (package / "helpers_other.py").write_text("value = 1\n")
    (package / "domain.py").write_text("import acme.helpers_other\n")
    spec = replace(
        load(project), boundaries=(Boundary(source="acme.domain", forbidden=("sqlite3",)),)
    )

    assert architecture(project, spec) == ()


@pytest.mark.parametrize(
    ("comment", "accepted"),
    [
        ("# ruff: noqa: F401", False),
        ("# flake8: noqa: F401", False),
        ("# ruff: noqa - intentional imports", False),
        ("# NOQA: F401", False),
        ("# ty: ignore", False),
        ("# ty: ignore - compatibility", False),
        ("# ty: ignore[] - compatibility", False),
        ("# ty: ignore[ ] - compatibility", False),
        ("# ty: ignore[invalid-return-type]", False),
        ("# type: ignore[] - compatibility", False),
        ("# pragma: no branch", False),
        ("# pragma: no cover", False),
        ("# noqa: F401 -", False),
        ("# noqa: F401 - public import # ty: ignore", False),
        ("# ruff: noqa: F401 - public re-export", True),
        ("# flake8: noqa: F401, F403 - compatibility exports", True),
        ("# NOQA: F401 - public re-export", True),
        ("# ty: ignore[invalid-return-type] - external stub mismatch", True),
        ("# ty: ignore[invalid-return-type, unresolved-import] - external stub mismatch", True),
        ("# type: ignore[assignment] - external stub mismatch", True),
        ("# pragma: no branch - loop always exits through return", True),
        ("# pragma: no cover - platform-specific fallback", True),
        ("# ordinary comment about ty and ruff", True),
        ("# noqa: F401 - public import # ty: ignore[unresolved-import] - optional API", True),
    ],
)
def test_every_suppression_needs_a_specific_rule_and_reason(
    project: Path, comment: str, accepted: bool
) -> None:
    source = project / "src/acme/__init__.py"
    source.write_text(comment + "\nvalue = 1\n")

    findings = suppressions(project, load(project))

    assert [(item.code, item.path) for item in findings] == (
        [] if accepted else [("suppression.reason", "src/acme/__init__.py")]
    )


@pytest.mark.parametrize(
    ("arguments", "source", "directives", "diagnostic"),
    [
        (
            ("ruff", "check", "--isolated", "--select", "F401"),
            "{directive}\nimport os\n",
            ("# ruff: noqa: F401", "# ruff: noqa: F401 - public compatibility import"),
            "F401",
        ),
        (
            ("ty", "check"),
            "def count() -> int:\n    return 'wrong'  {directive}\n",
            ("# ty: ignore", "# ty: ignore[invalid-return-type] - external stub mismatch"),
            "invalid-return-type",
        ),
    ],
)
@pytest.mark.parametrize("qualified", [False, True])
def test_real_tool_suppressions_require_a_specific_rule_and_reason(
    project: Path,
    arguments: tuple[str, ...],
    source: str,
    directives: tuple[str, str],
    diagnostic: str,
    qualified: bool,
) -> None:
    target = project / "src/acme/probe.py"
    target.write_text(source.format(directive=directives[int(qualified)]))
    suppressed = subprocess.run(  # noqa: S603 - locked engines on local controlled fixtures.
        [sys.executable, "-m", *arguments, str(target)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert suppressed.returncode == 0, suppressed.stdout + suppressed.stderr
    assert [item.code for item in suppressions(project, load(project))] == (
        [] if qualified else ["suppression.reason"]
    )

    target.write_text(source.format(directive=""))
    unsuppressed = subprocess.run(  # noqa: S603 - matching control without the suppression.
        [sys.executable, "-m", *arguments, str(target)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert unsuppressed.returncode == 1
    assert diagnostic in unsuppressed.stdout


@pytest.mark.parametrize(
    "artifact",
    [
        ".github/workflows/harness.yml",
        ".harness/gitlab-ci.yml",
        ".gitlab-ci.yml",
        ".harness/policy.md",
        ".harness/pre-commit-config.yaml",
        "AGENTS.md",
        "CLAUDE.md",
    ],
)
@pytest.mark.parametrize("remove", [False, True])
def test_managed_artifact_changes_invalidate_successful_reports(
    project: Path, artifact: str, remove: bool
) -> None:
    spec = load(project)
    apply(project, plan(project, spec))
    run_group(project, spec, "static")
    assert next(item for item in gate(project, spec) if item.code == "gate.static").status == "pass"
    target = project / artifact
    if remove:
        target.unlink()
    elif artifact in {"AGENTS.md", "CLAUDE.md"}:
        target.write_text(
            target.read_text().replace(BEGIN, BEGIN + "\nChanged managed instructions")
        )
    else:
        target.write_bytes(target.read_bytes() + b"\n# changed\n")

    assert next(item for item in gate(project, spec) if item.code == "gate.static").status == "fail"


def test_user_instruction_edits_outside_managed_blocks_keep_reports_current(project: Path) -> None:
    spec = load(project)
    apply(project, plan(project, spec))
    run_group(project, spec, "static")
    for name in ("AGENTS.md", "CLAUDE.md"):
        target = project / name
        target.write_text("# User instructions\n\n" + target.read_text() + "\nUser appendix.\n")

    assert next(item for item in gate(project, spec) if item.code == "gate.static").status == "pass"


def test_explicit_inputs_bind_the_entire_instruction_file(project: Path) -> None:
    spec = replace(load(project), inputs=("AGENTS.md",))
    apply(project, plan(project, spec))
    before = fingerprint(project, spec)
    target = project / "AGENTS.md"
    target.write_text(target.read_text() + "\nExplicitly tracked user instructions.\n")

    assert fingerprint(project, spec) != before


def test_malformed_managed_blocks_cannot_produce_successful_evidence(project: Path) -> None:
    spec = load(project)
    apply(project, plan(project, spec))
    (project / "AGENTS.md").write_text("missing managed markers\n")

    with pytest.raises(HarnessError, match="markers"):
        fingerprint(project, spec)


def test_a_command_cannot_change_a_managed_artifact_and_pass(project: Path) -> None:
    command = Check(
        id="edit-workflow",
        group="static",
        argv=(
            "@python",
            "-c",
            "from pathlib import Path; "
            "p = Path('.github/workflows/harness.yml'); "
            "p.write_text(p.read_text() + '\\n# edited\\n')",
        ),
    )
    spec = replace(load(project), checks=(command, load(project).checks[1]))
    apply(project, plan(project, spec))

    report = run_group(project, spec, "static")

    assert report["inputs_unchanged"] is False
    assert report["status"] == "fail"
