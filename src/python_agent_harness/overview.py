"""Read-only adoption overview; observations never become inferred policy."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .audit import fingerprint
from .config import SPEC_PATH, load
from .discovery import inspect_project
from .model import Finding, Spec
from .paths import inside
from .render import describe, plan
from .runner import gate, run_context


def render_preview(root: Path, spec: Spec) -> dict[str, object]:
    """Report conflicts without losing discovery or implying a partial plan."""
    try:
        return {"status": "ready", "changes": describe(root, plan(root, spec))}
    except (OSError, ValueError) as error:
        return {"status": "blocked", "error": str(error), "changes": None}


def report_shape(report: dict[str, Any], group: str, expected: list[str]) -> bool:
    """Check report structure before classifying its source and result."""
    return (
        type(report["schema_version"]) is int
        and report["schema_version"] == 1
        and report["group"] == group
        and isinstance(report["checks"], list)
        and isinstance(report["findings"], list)
        and [item["id"] for item in report["checks"]] == expected
        and type(report["inputs_unchanged"]) is bool
        and isinstance(report["fingerprint"], str)
        and isinstance(report["run"], str)
        and report["status"] in {"pass", "fail"}
        and all(
            item["status"] in {"pass", "fail", "blocked"}
            and (item["exit_code"] is None or type(item["exit_code"]) is int)
            and isinstance(item["detail"], str)
            for item in report["checks"]
        )
        and all(
            item["status"] in {"pass", "fail", "blocked", "review", "not_applicable"}
            and isinstance(item["code"], str)
            and isinstance(item["message"], str)
            and isinstance(item["path"], str)
            for item in report["findings"]
        )
    )


def report_state(root: Path, spec: Spec, finding: Finding, identity: str) -> dict[str, object]:
    """Describe a gate report without treating stale or malformed reports as runs."""
    path = inside(root, finding.path)
    if not path.exists():
        return {"evidence_state": "missing"}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        group = finding.code.removeprefix("gate.")
        expected = [check.id for check in spec.checks if check.group == group]
        checks = report["checks"]
        findings = report["findings"]
        if not report_shape(report, group, expected):
            return {"evidence_state": "malformed"}
        if (
            report["fingerprint"] != identity
            or report["run"] != run_context()
            or not report["inputs_unchanged"]
        ):
            return {"evidence_state": "stale"}
        if finding.status == "pass":
            return {"evidence_state": "current_pass"}
        failed = [
            {"id": item["id"], "status": item["status"], "exit_code": item["exit_code"]}
            for item in checks
            if item["status"] in {"fail", "blocked"}
        ]
        failed_findings = [item for item in findings if item["status"] in {"fail", "blocked"}]
        if report["status"] == "fail" and (failed or failed_findings):
            return {
                "evidence_state": "failed",
                "failed_checks": failed,
                "failed_findings": failed_findings,
            }
    except (OSError, ValueError, TypeError, KeyError):
        return {"evidence_state": "malformed"}
    return {"evidence_state": "malformed"}


def group_result(root: Path, spec: Spec, finding: Finding, identity: str) -> dict[str, object]:
    """Keep the gate result distinct from the overview's report validation."""
    state = report_state(root, spec, finding, identity)
    return {
        **asdict(finding),
        "gate_status": finding.status,
        "status": "pass" if state["evidence_state"] == "current_pass" else "fail",
        **state,
    }


def evidence_summary(root: Path, spec: Spec) -> dict[str, object]:
    """Reuse the gate, whose validation includes fingerprint and run context."""
    try:
        findings = gate(root, spec)
        identity = fingerprint(root, spec)
        groups = [group_result(root, spec, item, identity) for item in findings]
    except (OSError, ValueError) as error:
        return {"status": "unavailable", "error": str(error), "groups": None}
    return {"status": "observed", "groups": groups}


def requirement_status(group: str, finding: dict[str, object]) -> str:
    """A group failure does not say that its individual requirement failed."""
    if group == "deep":
        return "optional_not_evaluated"
    if finding.get("evidence_state") == "current_pass":
        return "current_group_pass"
    if "evidence_state" in finding:
        return f"group_{finding['evidence_state']}"
    return "unverified"


def requirement_evidence(spec: Spec, group_evidence: dict[str, object]) -> list[dict[str, object]]:
    """Connect each requirement to its group without claiming semantic correctness."""
    checks = {check.id: check for check in spec.checks}
    groups = group_evidence.get("groups")
    results = {item["code"]: item for item in groups} if isinstance(groups, list) else {}
    summary: list[dict[str, object]] = []
    for requirement in spec.requirements:
        entry = asdict(requirement)
        entry["group"] = None
        entry["evidence_status"] = "review_required"
        if requirement.enforcement != "review":
            group = checks[requirement.check].group
            entry["group"] = group
            finding = results.get(f"gate.{group}", {})
            entry["evidence_status"] = requirement_status(group, finding)
        summary.append(entry)
    return summary


def specification_overview(root: Path, spec: Spec, preview: dict[str, object]) -> dict[str, object]:
    """List declared checks and review requirements without asserting approval."""
    evidence = evidence_summary(root, spec)
    return {
        "status": "valid",
        "path": SPEC_PATH,
        "checks": [asdict(check) for check in spec.checks],
        "requirements": requirement_evidence(spec, evidence),
        "boundaries": [asdict(boundary) for boundary in spec.boundaries],
        "setup": spec.setup,
        "sources": spec.sources,
        "tests": spec.tests,
        "providers": spec.providers,
        "note": "Configuration is declared; human agreement and execution are not inferred.",
        "preview": preview,
        "evidence": evidence,
    }


def overview(root: Path) -> dict[str, object]:
    """Keep missing or invalid specifications visible alongside observed facts."""
    result: dict[str, object] = {
        "schema_version": 1,
        "inspection": inspect_project(root),
        "limits": [
            "Tool declarations and files do not establish execution or enforcement.",
            "Discovery is not exhaustive; command files are not parsed or executed.",
            "Review requirements and test oracle quality need human judgment.",
            "Server protection is unverified; use doctor for a live read-only check.",
            "Deep checks are optional and are not validated by the required gate.",
        ],
    }
    path = inside(root, SPEC_PATH)
    if not path.exists():
        result["status"] = "missing"
        result["specification"] = {"status": "missing", "path": SPEC_PATH}
        return result
    try:
        spec = load(root)
        preview = render_preview(root, spec)
        result["specification"] = specification_overview(root, spec, preview)
        result["status"] = "blocked" if preview["status"] == "blocked" else "valid"
    except (OSError, ValueError) as error:
        result["status"] = "blocked"
        result["specification"] = {"status": "blocked", "path": SPEC_PATH, "error": str(error)}
    return result
