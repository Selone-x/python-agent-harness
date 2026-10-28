"""The overview separates discovered facts, render plans and actual evidence."""

import json
from pathlib import Path
from typing import Any

import pytest

from python_agent_harness.cli import main
from python_agent_harness.config import load
from python_agent_harness.runner import run_group


def read_overview(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any]]:
    """Exercise the public command and decode its JSON output."""
    status = main(["--root", str(root), "overview"])
    return status, json.loads(capsys.readouterr().out)


def test_unconfigured_project_is_inspected_without_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.black]\nline-length = 88\n")
    (tmp_path / "poetry.lock").write_text("locked")
    (tmp_path / "AGENTS.md").write_text("Existing instructions\n")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    status, report = read_overview(tmp_path, capsys)

    assert status == 0
    assert report["inspection"]["tool_evidence"]["black"]["configuration"] == ["tool.black"]
    assert report["inspection"]["lockfiles"] == ["poetry.lock"]
    assert report["inspection"]["instructions"] == ["AGENTS.md"]
    assert report["specification"] == {"status": "missing", "path": ".harness/project.toml"}
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_poetry_groups_and_existing_command_files_are_visible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poetry.group.dev.dependencies]\nblack = "^24"\nmypy = "^1"\n'
        '[tool.poetry.group.test.dependencies]\npytest = "^8"\n'
    )
    (tmp_path / "Makefile").write_text("check:\n\tpoetry run black --check .\n")
    status, report = read_overview(tmp_path, capsys)

    assert status == 0
    inspection = report["inspection"]
    assert inspection["tool_evidence"]["black"]["dependencies"] == ["poetry-group:dev"]
    assert inspection["tool_evidence"]["mypy"]["dependencies"] == ["poetry-group:dev"]
    assert inspection["tool_evidence"]["pytest"]["dependencies"] == ["poetry-group:test"]
    assert inspection["command_files"] == ["Makefile"]
    assert any("not exhaustive" in limit for limit in report["limits"])


def test_configured_project_reports_preview_and_required_evidence(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = {
        path.relative_to(project): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }

    status, report = read_overview(project, capsys)

    spec = report["specification"]
    assert status == 0
    assert spec["status"] == "valid"
    assert spec["requirements"][0]["enforcement"] == "review"
    assert spec["requirements"][0]["evidence_status"] == "review_required"
    assert spec["checks"][0]["argv"] == ["@python", "-c", "pass"]
    assert spec["preview"]["status"] == "ready"
    assert any(change["path"] == "AGENTS.md" for change in spec["preview"]["changes"])
    assert [group["status"] for group in spec["evidence"]["groups"]] == ["fail", "fail"]
    assert any("Server protection is unverified" in item for item in report["limits"])
    after = {
        path.relative_to(project): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_only_current_successful_group_evidence_is_reported_as_pass(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_group(project, load(project), "static")
    _, report = read_overview(project, capsys)
    groups = report["specification"]["evidence"]["groups"]
    assert [(group["code"], group["status"]) for group in groups] == [
        ("gate.static", "pass"),
        ("gate.tests", "fail"),
    ]

    (project / "src/acme/__init__.py").write_text("value = 2\n")
    _, stale = read_overview(project, capsys)
    assert stale["specification"]["evidence"]["groups"][0]["status"] == "fail"


def test_preview_conflict_is_visible_without_overwriting(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = project / ".harness/policy.md"
    path.write_text("User policy\n")

    status, report = read_overview(project, capsys)

    preview = report["specification"]["preview"]
    assert status == 2
    assert report["status"] == "blocked"
    assert report["specification"]["status"] == "valid"
    assert preview["status"] == "blocked"
    assert "unowned" in preview["error"]
    assert preview["changes"] is None
    assert path.read_text() == "User policy\n"


def test_invalid_specification_preserves_inspection(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / ".harness/project.toml").write_text("unknown = true\n")

    status, report = read_overview(project, capsys)

    assert status == 2
    assert report["inspection"]["source_candidates"] == ["src"]
    assert report["specification"]["status"] == "blocked"
    assert "Unknown project keys" in report["specification"]["error"]


def test_missing_declared_evidence_blocks_gate_summary(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / "tests/test_contract.py").write_text("def test_contract(): pass\n")
    config = project / ".harness/project.toml"
    with config.open("a") as output:
        output.write(
            '\n[[requirements]]\nid = "rule"\ndescription = "Rule"\n'
            'enforcement = "test"\ncheck = "format"\nevidence = ["tests/test_contract.py"]\n'
        )
    (project / "src/acme/__init__.py").unlink()
    (project / "src/acme").rmdir()

    _, report = read_overview(project, capsys)

    evidence = report["specification"]["evidence"]
    assert evidence["status"] == "unavailable"
    assert "Source does not exist" in evidence["error"]
    assert evidence["groups"] is None
    assert report["specification"]["requirements"][1]["evidence_status"] == "unverified"


def test_requirement_group_evidence_and_optional_checks_are_distinguished(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / "tests/test_contract.py").write_text("def test_contract(): pass\n")
    config = project / ".harness/project.toml"
    with config.open("a") as output:
        output.write(
            '\n[[checks]]\nid = "deep-check"\ngroup = "deep"\nargv = ["@python", "-c", "pass"]\n'
            '\n[[requirements]]\nid = "static-rule"\ndescription = "Static rule"\n'
            'enforcement = "test"\ncheck = "format"\nevidence = ["tests/test_contract.py"]\n'
            '\n[[requirements]]\nid = "deep-rule"\ndescription = "Deep rule"\n'
            'enforcement = "check"\ncheck = "deep-check"\nevidence = ["tests/test_contract.py"]\n'
        )

    _, report = read_overview(project, capsys)
    assert [item["evidence_status"] for item in report["specification"]["requirements"]] == [
        "review_required",
        "group_missing",
        "optional_not_evaluated",
    ]
    run_group(project, load(project), "static")
    _, report = read_overview(project, capsys)
    requirement = report["specification"]["requirements"][1]
    assert requirement["group"] == "static"
    assert requirement["evidence_status"] == "current_group_pass"
    assert requirement["evidence"] == ["tests/test_contract.py"]


def test_evidence_distinguishes_missing_failed_stale_and_malformed(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = project / ".harness/project.toml"
    config.write_text(config.read_text().replace('"pass"', '"raise SystemExit(7)"', 1))
    _, report = read_overview(project, capsys)
    assert report["specification"]["evidence"]["groups"][0]["evidence_state"] == "missing"

    run_group(project, load(project), "static")
    _, report = read_overview(project, capsys)
    group = report["specification"]["evidence"]["groups"][0]
    assert group["evidence_state"] == "failed"
    assert group["failed_checks"] == [{"id": "format", "status": "fail", "exit_code": 7}]

    (project / "src/acme/__init__.py").write_text("value = 2\n")
    _, report = read_overview(project, capsys)
    assert report["specification"]["evidence"]["groups"][0]["evidence_state"] == "stale"

    (project / ".harness/reports/static.json").write_text("{")
    _, report = read_overview(project, capsys)
    assert report["specification"]["evidence"]["groups"][0]["evidence_state"] == "malformed"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("schema_version", 2, "malformed"),
        ("group", "tests", "malformed"),
        ("checks", {}, "malformed"),
        ("findings", {}, "malformed"),
        ("checks", [], "malformed"),
        ("inputs_unchanged", "yes", "malformed"),
        ("fingerprint", None, "malformed"),
        ("run", 42, "malformed"),
        ("status", "skipped", "malformed"),
        ("status", "fail", "malformed"),
        ("checks", [{"id": "format", "status": "unknown", "exit_code": 0}], "malformed"),
        (
            "checks",
            [{"id": "format", "status": "fail", "exit_code": False, "detail": "finished"}],
            "malformed",
        ),
        ("findings", [{"status": "unknown"}], "malformed"),
        ("findings", [{"status": "fail", "code": "failure"}], "malformed"),
        ("fingerprint", "previous", "stale"),
        ("run", "github:other:1", "stale"),
        ("inputs_unchanged", False, "stale"),
    ],
)
def test_invalid_group_report_never_becomes_current_failure(
    project: Path, capsys: pytest.CaptureFixture[str], field: str, value: object, expected: str
) -> None:
    run_group(project, load(project), "static")
    path = project / ".harness/reports/static.json"
    original = json.loads(path.read_text())
    path.write_text(json.dumps({**original, field: value}))

    _, report = read_overview(project, capsys)

    assert report["specification"]["evidence"]["groups"][0]["evidence_state"] == expected


def test_current_coverage_failure_is_reported_as_a_failed_group(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_group(project, load(project), "tests")

    _, report = read_overview(project, capsys)

    group = report["specification"]["evidence"]["groups"][1]
    assert group["evidence_state"] == "failed"
    assert group["failed_checks"] == []
    assert group["failed_findings"][0]["code"] == "coverage.invalid"
