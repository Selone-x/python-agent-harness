"""Coverage ratios and source inventory, checked independently and exactly."""

import json
from decimal import Decimal
from pathlib import Path

from .model import Finding, Spec
from .paths import HarnessError, inside, source_files

COUNTERS = ("covered_lines", "num_statements", "covered_branches", "num_branches")


def counters(value: object) -> dict[str, int]:
    """Reject malformed, negative, boolean and inflated coverage counters."""
    if not isinstance(value, dict):
        raise HarnessError("Coverage summary must be a JSON object")
    result: dict[str, int] = {}
    for key in COUNTERS:
        item = value.get(key)
        if type(item) is not int or item < 0:
            raise HarnessError(f"Invalid coverage counter: {key}")
        result[key] = item
    if (
        result["covered_lines"] > result["num_statements"]
        or result["covered_branches"] > result["num_branches"]
    ):
        raise HarnessError("Covered counters exceed executable counters")
    return result


def verify_coverage(root: Path, spec: Spec) -> tuple[Finding, ...]:
    """Never treat a missing file or branchless program as hidden coverage debt."""
    data = json.loads(inside(root, spec.coverage).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise HarnessError("Coverage must contain a per-file inventory")
    totals = counters(data.get("totals"))
    expected = {path.resolve() for path in source_files(root, spec.sources)}
    actual: set[Path] = set()
    summed = dict.fromkeys(COUNTERS, 0)
    for name, entry in data["files"].items():
        path = Path(name)
        resolved = (root / path).resolve()
        if resolved in actual or not resolved.is_relative_to(root):
            raise HarnessError("Duplicate or external coverage source")
        actual.add(resolved)
        if not isinstance(entry, dict):
            raise HarnessError("Invalid per-file coverage")
        for key, value in counters(entry.get("summary")).items():
            summed[key] += value
    if summed != totals or totals["num_statements"] == 0:
        raise HarnessError("Coverage totals are inconsistent or contain no executable statements")
    findings = [
        Finding(
            code="coverage.inventory",
            status="pass" if actual == expected else "fail",
            message=(
                f"Missing: {sorted(str(p) for p in expected - actual)}; "
                f"unexpected: {sorted(str(p) for p in actual - expected)}"
            ),
        )
    ]
    for label, covered, total, threshold in (
        ("lines", totals["covered_lines"], totals["num_statements"], spec.line_minimum),
        ("branches", totals["covered_branches"], totals["num_branches"], spec.branch_minimum),
    ):
        passes = Decimal(covered) * 100 >= Decimal(total) * Decimal(threshold)
        findings.append(
            Finding(
                code=f"coverage.{label}",
                status="pass" if passes else "fail",
                message=f"{covered}/{total}; required {threshold}%",
            )
        )
    return tuple(findings)
