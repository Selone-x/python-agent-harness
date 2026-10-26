"""Platform facts are checked separately from generated policy intentions."""

import json
from pathlib import Path

import pytest

from python_agent_harness.cli import main
from python_agent_harness.discovery import inspect_project
from python_agent_harness.paths import HarnessError
from python_agent_harness.providers import github_findings, gitlab_findings


def test_github_missing_protections_are_not_success() -> None:
    assert all(item.status == "blocked" for item in github_findings({}))
    with pytest.raises(HarnessError):
        github_findings(None)


def test_github_required_exact_gate_and_independent_fresh_review() -> None:
    data = {
        "required_status_checks": {"strict": True, "checks": [{"context": "harness-gate"}]},
        "required_pull_request_reviews": {
            "require_code_owner_reviews": True,
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_last_push_approval": True,
            "bypass_pull_request_allowances": {},
        },
        "enforce_admins": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
    }

    assert all(item.status == "pass" for item in github_findings(data))


def test_gitlab_optional_approval_and_permissive_wildcard_are_blocked() -> None:
    project = {
        "default_branch": "main",
        "only_allow_merge_if_pipeline_succeeds": True,
        "allow_merge_on_skipped_pipeline": False,
    }
    branches = [
        {"name": "main", "allow_force_push": False, "push_access_levels": [{"access_level": 0}]},
        {"name": "*", "allow_force_push": False, "push_access_levels": [{"access_level": 40}]},
    ]

    findings = gitlab_findings(project, branches, None)

    assert [item.status for item in findings] == ["pass", "blocked", "blocked"]


def test_gitlab_restricted_branch_and_required_approvals() -> None:
    project = {
        "default_branch": "main",
        "only_allow_merge_if_pipeline_succeeds": True,
        "allow_merge_on_skipped_pipeline": False,
    }
    branches = [
        {"name": "main", "allow_force_push": False, "push_access_levels": [{"access_level": 0}]}
    ]
    approvals = {
        "approvals_before_merge": 1,
        "disable_overriding_approvers_per_merge_request": True,
        "reset_approvals_on_push": True,
    }

    assert all(item.status == "pass" for item in gitlab_findings(project, branches, approvals))
    with pytest.raises(HarnessError):
        gitlab_findings(None, [], None)


def test_inspection_preserves_existing_toolchain(project: Path) -> None:
    metadata = project / "pyproject.toml"
    metadata.write_text(
        '[project]\nname = "existing"\n[tool.black]\nline-length=88\n[tool.mypy]\nstrict=true\n',
        encoding="utf-8",
    )
    (project / "poetry.lock").write_text("locked", encoding="utf-8")

    facts = inspect_project(project)

    assert facts["tools"] == ["black", "mypy"]
    assert facts["lockfiles"] == ["poetry.lock"]
    assert metadata.read_text().startswith("[project]")


@pytest.mark.parametrize("command", ["inspect", "validate", "render"])
def test_read_only_cli_commands_do_not_write(
    project: Path, command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    before = {path.relative_to(project) for path in project.rglob("*")}

    assert main(["--root", str(project), command]) == 0
    assert {path.relative_to(project) for path in project.rglob("*")} == before
    assert isinstance(json.loads(capsys.readouterr().out), dict)


def test_cli_preview_apply_check_audit_and_gate(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prefix = ["--root", str(project)]

    assert main([*prefix, "render", "--check"]) == 1
    assert main([*prefix, "render", "--apply"]) == 0
    assert main([*prefix, "render", "--check"]) == 0
    assert main([*prefix, "audit"]) == 0
    assert main([*prefix, "gate"]) == 1
    assert main([*prefix, "setup"]) == 0
    assert main([*prefix, "check", "--group", "static"]) == 0
    assert main([*prefix, "check", "--group", "tests"]) == 1
    assert main([*prefix, "render", "--check", "--apply"]) == 2
    assert "Review expected values" in capsys.readouterr().out


def test_cli_init_and_invalid_configuration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "new"
    prefix = ["--root", str(root)]

    assert (
        main(
            [
                *prefix,
                "init",
                "--name",
                "demo",
                "--package",
                "demo",
                "--kind",
                "service",
                "--scaffold",
            ]
        )
        == 0
    )
    assert main([*prefix, "validate"]) == 0
    (root / ".harness/project.toml").write_text("typo = true", encoding="utf-8")
    assert main([*prefix, "validate"]) == 2
    assert '"status": "blocked"' in capsys.readouterr().out


def test_cli_package_missing_artifacts(project: Path) -> None:
    assert main(["--root", str(project), "package", "--module", "acme"]) == 2
