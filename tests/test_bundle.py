"""The distributed runtime must validate itself and expose reviewable changes."""

import subprocess
import sys
from pathlib import Path

from python_agent_harness.config import load
from python_agent_harness.render import apply, describe, plan


def test_preview_contains_real_diffs_before_writes(project: Path) -> None:
    agents = project / "AGENTS.md"
    agents.write_text("# Keep my rules\n", encoding="utf-8")
    changes = plan(project, load(project))
    preview = {item["path"]: item for item in describe(project, changes)}

    assert "+Read `.harness/policy.md`" in str(preview["AGENTS.md"]["diff"])
    assert preview[".harness/runner.pyz"]["diff"] is None
    assert len(str(preview[".harness/runner.pyz"]["sha256"])) == 64
    assert agents.read_text() == "# Keep my rules\n"


def test_bundle_can_verify_its_own_generated_outputs(project: Path) -> None:
    apply(project, plan(project, load(project)))

    result = subprocess.run(  # noqa: S603 - fixed isolated interpreter and local generated runner.
        [sys.executable, "-I", str(project / ".harness/runner.pyz"), "render", "--check"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stdout
