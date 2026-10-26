"""Generation owns only known files and preserves user instructions."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from python_agent_harness.audit import audit_project, ownership
from python_agent_harness.bootstrap import initialize
from python_agent_harness.config import load
from python_agent_harness.model import successful
from python_agent_harness.paths import HarnessError
from python_agent_harness.render import (
    BEGIN,
    END,
    apply,
    block_content,
    merge_block,
    plan,
    runner_bundle,
)


def test_render_preview_apply_and_idempotency(project: Path) -> None:
    changes = plan(project, load(project))

    assert not (project / "AGENTS.md").exists()
    assert ".harness/runner.pyz" in changes
    apply(project, changes)
    assert plan(project, load(project)) == {}
    assert successful(audit_project(project, load(project)))


def test_surrounding_instructions_survive_edit_and_update(project: Path) -> None:
    agents = project / "AGENTS.md"
    agents.write_text("# My architecture\nKeep Poetry.\n", encoding="utf-8")
    apply(project, plan(project, load(project)))
    agents.write_text(agents.read_text() + "\nNew independent rule.\n", encoding="utf-8")

    assert ownership(project) == ()
    assert plan(project, load(project)) == {}
    assert "Keep Poetry." in agents.read_text()
    assert "New independent rule." in agents.read_text()


def test_edited_owned_content_fails_before_any_write(project: Path) -> None:
    apply(project, plan(project, load(project)))
    policy = project / ".harness/policy.md"
    policy.write_text("weakened", encoding="utf-8")
    before = (project / "AGENTS.md").read_bytes()

    with pytest.raises(HarnessError, match="Conflict"):
        plan(project, load(project))
    assert (project / "AGENTS.md").read_bytes() == before
    assert ownership(project)[0].code == "render.drift"


def test_unowned_workflow_never_overwritten(project: Path) -> None:
    workflow = project / ".github/workflows/harness.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("custom workflow", encoding="utf-8")

    with pytest.raises(HarnessError, match="unowned"):
        plan(project, load(project))
    assert not (project / ".harness/runner.pyz").exists()


def test_existing_gitlab_jobs_are_preserved(project: Path) -> None:
    ci = project / ".gitlab-ci.yml"
    original = b"stages: [deploy]\nrelease:\n  stage: deploy\n  script: echo deploy\n"
    ci.write_bytes(original)

    apply(project, plan(project, load(project)))

    assert ci.read_bytes() == original
    generated = yaml.safe_load((project / ".harness/gitlab-ci.yml").read_text())
    assert generated["harness-gate"]["when"] == "always"
    assert generated["harness-static"]["allow_failure"] is False


def test_ci_groups_and_aggregate_gate_are_explicit(project: Path) -> None:
    apply(project, plan(project, load(project)))
    github = yaml.safe_load((project / ".github/workflows/harness.yml").read_text())

    assert github["jobs"]["checks"]["strategy"]["matrix"]["group"] == ["static", "tests"]
    assert github["jobs"]["gate"]["needs"] == ["checks"]
    assert github["jobs"]["gate"]["if"] == "${{ always() }}"
    assert github["permissions"] == {"contents": "read"}


def test_bundle_is_reproducible_and_runs_without_project_imports(project: Path) -> None:
    assert runner_bundle() == runner_bundle()
    apply(project, plan(project, load(project)))
    (project / "json.py").write_text("raise RuntimeError('shadowed stdlib')", encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - fixed isolated interpreter and local generated runner.
        [sys.executable, "-I", str(project / ".harness/runner.pyz"), "validate"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0
    assert '"name": "example"' in result.stdout


@pytest.mark.parametrize(
    "content", [b"no markers", f"{BEGIN}\n{BEGIN}\n{END}".encode(), f"{END}\n{BEGIN}".encode()]
)
def test_invalid_instruction_markers(content: bytes) -> None:
    with pytest.raises(HarnessError):
        block_content(content)


def test_merge_empty_block() -> None:
    wanted = f"{BEGIN}\nrule\n{END}\n".encode()

    assert merge_block(b"", wanted) == wanted


def test_gitlab_only_does_not_generate_github_workflow(project: Path) -> None:
    policy = project / ".harness/project.toml"
    policy.write_text(
        policy.read_text().replace('["github", "gitlab"]', '["gitlab"]'),
        encoding="utf-8",
    )

    changes = plan(project, load(project))

    assert ".github/workflows/harness.yml" not in changes
    root = yaml.safe_load(changes[".gitlab-ci.yml"])
    assert root["workflow"]["rules"][0] == {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"'}


def test_provider_removal_requires_review(project: Path) -> None:
    apply(project, plan(project, load(project)))
    policy = project / ".harness/project.toml"
    policy.write_text(
        policy.read_text().replace('["github", "gitlab"]', '["github"]'), encoding="utf-8"
    )

    with pytest.raises(HarnessError, match="removal"):
        plan(project, load(project))


def test_adoption_only_creates_a_draft(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.black]\nline-length = 88\n", encoding="utf-8")
    before = (tmp_path / "pyproject.toml").read_bytes()

    created = initialize(tmp_path, "example", "example", "service", ("github",), False)

    assert created == (".harness/project.toml",)
    assert (tmp_path / "pyproject.toml").read_bytes() == before
    assert "Agree existing" in load(tmp_path).checks[0].argv[-1]


@pytest.mark.parametrize("kind", ["library", "service", "cli", "research"])
def test_new_project_kinds_have_appropriate_groups(tmp_path: Path, kind: str) -> None:
    initialize(tmp_path, "example-project", "example_project", kind, ("github", "gitlab"), True)
    spec = load(tmp_path)

    assert ("package" in {item.group for item in spec.checks}) is (kind == "library")
    assert (tmp_path / "tests/test_package.py").is_file()


def test_init_refuses_invalid_names_nonempty_or_existing_spec(project: Path) -> None:
    for name, package in (("../bad", "acme"), ("good", "bad-name"), ("good", "acme")):
        with pytest.raises(HarnessError):
            initialize(project, name, package, "service", ("github",), False)
    with pytest.raises(HarnessError):
        initialize(project, "good", "acme", "service", ("github",), True)
