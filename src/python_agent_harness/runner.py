"""Bounded sequential commands and evidence-bound CI aggregation."""

import json
import os
import selectors
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .audit import fingerprint
from .coverage import verify_coverage
from .model import Check, CommandResult, Finding, Spec, successful
from .paths import HarnessError, inside


def expand(root: Path, argv: tuple[str, ...]) -> list[str]:
    """Resolve documented executable aliases, keeping all arguments separate."""
    if argv[0] == "@harness":
        return [sys.executable, "-I", str(inside(root, ".harness/runner.pyz")), *argv[1:]]
    return [sys.executable if value == "@python" else value for value in argv]


def terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop the process group so timed-out commands cannot leave workers behind."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def collect(process: subprocess.Popen[bytes], log: Path, deadline: float, limit: int) -> str:
    """Drain stdout with bounded memory and disk use, including inherited pipes."""
    if process.stdout is None:
        raise HarnessError("Command output pipe is unavailable")
    total = 0
    with selectors.DefaultSelector() as selector, log.open("wb") as output:
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map():
            if time.monotonic() >= deadline:
                return "timeout"
            for key, _ in selector.select(timeout=0.05):
                chunk = os.read(key.fd, 65_536)
                if not chunk:
                    selector.unregister(key.fd)
                    continue
                output.write(chunk[: max(0, limit - total)])
                total += len(chunk)
                if total > limit:
                    return "output_limit"
        remaining = max(0.001, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            return "timeout"
    return "finished"


def execute(
    root: Path, command: Check, output_limit: int, timeout: float | None = None
) -> CommandResult:
    """A nonzero exit, timeout, missing executable or output flood fails the check."""
    log = inside(root, f".harness/reports/logs/{command.id}.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with subprocess.Popen(  # noqa: S603 - approved spec argv, no shell, bounded process group.
            expand(root, command.argv),
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process:
            try:
                reason = collect(
                    process, log, time.monotonic() + (timeout or command.timeout), output_limit
                )
            finally:
                terminate(process)
            return CommandResult(
                id=command.id,
                status="pass" if reason == "finished" and process.returncode == 0 else "fail",
                exit_code=process.returncode,
                detail=reason,
            )
    except OSError as error:
        return CommandResult(id=command.id, status="blocked", exit_code=None, detail=str(error))


def run_setup(root: Path, spec: Spec) -> tuple[CommandResult, ...]:
    """Setup is explicit, sequential and subject to the same command budgets."""
    result: list[CommandResult] = []
    for index, argv in enumerate(spec.setup):
        command = Check(id=f"setup-{index}", group="static", argv=argv, timeout=600)
        item = execute(root, command, spec.output_limit)
        result.append(item)
        if item.status != "pass":
            break
    return tuple(result)


def fresh_coverage(root: Path, spec: Spec, previous: int | None) -> tuple[Finding, ...]:
    """Require this run's coverage report before checking inventory and ratios."""
    try:
        path = inside(root, spec.coverage)
        if previous is not None and path.stat().st_mtime_ns == previous:
            raise HarnessError("Coverage report was not refreshed by this test run")
        return verify_coverage(root, spec)
    except (OSError, ValueError) as error:
        return (Finding(code="coverage.invalid", status="fail", message=str(error)),)


def group_checks(
    root: Path, spec: Spec, group: str
) -> tuple[tuple[CommandResult, ...], tuple[Finding, ...]]:
    """Execute every required command and independently validate fresh coverage."""
    selected = tuple(item for item in spec.checks if item.group == group)
    if not selected:
        raise HarnessError(f"No configured checks for group {group}")
    coverage_path = inside(root, spec.coverage)
    previous = coverage_path.stat().st_mtime_ns if coverage_path.exists() else None
    results: list[CommandResult] = []
    start = time.monotonic()
    for check in selected:
        remaining = (
            spec.deep_budget - (time.monotonic() - start) if group == "deep" else check.timeout
        )
        if remaining <= 0:
            results.append(
                CommandResult(
                    id=check.id, status="blocked", exit_code=None, detail="deep budget exhausted"
                )
            )
        else:
            results.append(execute(root, check, spec.output_limit, min(check.timeout, remaining)))
    findings = fresh_coverage(root, spec, previous) if group == "tests" else ()
    return tuple(results), findings


def run_group(root: Path, spec: Spec, group: str) -> dict[str, object]:
    """Persist observed results; bind them to the unchanged inputs of this run."""
    before = fingerprint(root, spec)
    results, findings = group_checks(root, spec, group)
    unchanged = fingerprint(root, spec) == before
    report: dict[str, object] = {
        "schema_version": 1,
        "group": group,
        "fingerprint": before,
        "status": "pass"
        if unchanged and all(item.status == "pass" for item in results) and successful(findings)
        else "fail",
        "inputs_unchanged": unchanged,
        "run": run_context(),
        "checks": [asdict(item) for item in results],
        "findings": [asdict(item) for item in findings],
    }
    path = inside(root, f".harness/reports/{group}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def gate(root: Path, spec: Spec) -> tuple[Finding, ...]:
    """Skipped, stale, absent and malformed required job results cannot pass."""
    findings: list[Finding] = []
    identity = fingerprint(root, spec)
    for group in sorted({check.group for check in spec.checks} - {"deep"}):
        path = inside(root, f".harness/reports/{group}.json")
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            expected = [item.id for item in spec.checks if item.group == group]
            observed = report["checks"]
            valid = (
                type(report["schema_version"]) is int
                and report["schema_version"] == 1
                and report["group"] == group
                and report["fingerprint"] == identity
                and report["run"] == run_context()
                and report["inputs_unchanged"] is True
                and report["status"] == "pass"
                and [item["id"] for item in observed] == expected
                and all(
                    item["status"] == "pass"
                    and type(item["exit_code"]) is int
                    and item["exit_code"] == 0
                    and item["detail"] == "finished"
                    for item in observed
                )
                and isinstance(report["findings"], list)
                and all(
                    item["status"] in {"pass", "review", "not_applicable"}
                    for item in report["findings"]
                )
                and coverage_evidence(group, report["findings"])
            )
        except (OSError, ValueError, KeyError, TypeError):
            valid = False
        findings.append(
            Finding(
                code=f"gate.{group}",
                status="pass" if valid else "fail",
                message="Observed required job evidence is current and successful"
                if valid
                else "Required job evidence is absent, stale, unsuccessful or malformed",
                path=path.relative_to(root).as_posix(),
            )
        )
    return tuple(findings)


def run_context() -> str:
    """CI artifacts from another pipeline or workflow attempt cannot be replayed."""
    if identifier := os.environ.get("GITHUB_RUN_ID"):
        return f"github:{identifier}:{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    if identifier := os.environ.get("CI_PIPELINE_ID"):
        return f"gitlab:{identifier}"
    return "local"


def coverage_evidence(group: str, findings: list[dict[str, object]]) -> bool:
    """A successful test report must include every independent coverage gate."""
    if group != "tests":
        return True
    expected = {"coverage.inventory", "coverage.lines", "coverage.branches"}
    return (
        len(findings) == 3
        and {item["code"] for item in findings} == expected
        and all(item["status"] == "pass" for item in findings)
    )
