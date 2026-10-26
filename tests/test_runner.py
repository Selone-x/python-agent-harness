"""Real finite child processes verify budgets and evidence binding."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from python_agent_harness.config import load
from python_agent_harness.model import Check
from python_agent_harness.paths import HarnessError
from python_agent_harness.runner import execute, expand, gate, run_group, run_setup


@pytest.mark.parametrize(
    "code,status,exit_code",
    [
        ("pass", "pass", 0),
        ("raise SystemExit(7)", "fail", 7),
        ("raise RuntimeError('expected')", "fail", 1),
    ],
)
def test_actual_exit_codes(project: Path, code: str, status: str, exit_code: int) -> None:
    command = Check(id="command", group="static", argv=("@python", "-c", code))

    result = execute(project, command, 2048)

    assert (result.status, result.exit_code, result.detail) == (status, exit_code, "finished")


def test_missing_executable_is_blocked(project: Path) -> None:
    result = execute(
        project,
        Check(id="missing", group="static", argv=("/definitely/missing/harness-command",)),
        2048,
    )

    assert result.status == "blocked"
    assert result.exit_code is None


def test_timeout_stops_unbounded_child(project: Path) -> None:
    command = Check(id="timeout", group="static", argv=("@python", "-c", "while True: pass"))

    result = execute(project, command, 2048, timeout=0.1)

    assert result.status == "fail"
    assert result.detail == "timeout"
    assert result.exit_code is not None


def test_output_flood_is_stopped_and_disk_bounded(project: Path) -> None:
    command = Check(
        id="flood", group="static", argv=("@python", "-c", "import os; os.write(1, b'x' * 100000)")
    )

    result = execute(project, command, 1000)

    assert result.detail == "output_limit"
    assert (project / ".harness/reports/logs/flood.log").stat().st_size == 1000


def test_setup_stops_after_failure(project: Path) -> None:
    spec = replace(
        load(project), setup=(("@python", "-c", "raise SystemExit(1)"), ("@python", "-c", "pass"))
    )

    assert len(run_setup(project, spec)) == 1


def test_argv_alias_does_not_expand_shell(project: Path) -> None:
    command = expand(project, ("echo", "$(touch victim)", "a b"))

    assert command == ["echo", "$(touch victim)", "a b"]
    assert "-I" in expand(project, ("@harness", "validate"))


def test_missing_group_and_fresh_coverage_are_required(project: Path) -> None:
    spec = load(project)
    with pytest.raises(HarnessError, match="No configured"):
        run_group(project, spec, "package")

    assert run_group(project, spec, "tests")["status"] == "fail"
    assert all(item.status == "fail" for item in gate(project, spec))


def test_current_required_job_evidence_passes_and_tampering_fails(project: Path) -> None:
    spec = load(project)
    run_group(project, spec, "static")
    report_path = project / ".harness/reports/static.json"
    original = json.loads(report_path.read_text())

    assert gate(project, spec)[0].status == "pass"
    for key, value in (
        ("status", "skipped"),
        ("fingerprint", "old"),
        ("inputs_unchanged", False),
        ("checks", []),
        ("schema_version", 2),
    ):
        changed = {**original, key: value}
        report_path.write_text(json.dumps(changed), encoding="utf-8")
        assert gate(project, spec)[0].status == "fail"


def test_stale_coverage_is_not_reused(project: Path) -> None:
    coverage = project / ".harness/reports/coverage.json"
    coverage.parent.mkdir()
    coverage.write_text("{}", encoding="utf-8")

    report = run_group(project, load(project), "tests")

    assert report["status"] == "fail"
    assert "not refreshed" in str(report["findings"])
