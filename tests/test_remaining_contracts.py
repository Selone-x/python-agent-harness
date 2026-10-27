"""Independent acceptance for replay, extension inputs and failed integrations."""

import ast
import io
import json
import subprocess
import sys
import tarfile
import time
from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile

import pytest
from test_audit_coverage import coverage_data

from python_agent_harness import cli, providers
from python_agent_harness.audit import audit_project, fingerprint, imports, ownership, suppressions
from python_agent_harness.config import boundaries, load
from python_agent_harness.model import Check, Finding, successful
from python_agent_harness.package import verify_package
from python_agent_harness.paths import HarnessError
from python_agent_harness.render import BEGIN, END, apply, merge_block, plan
from python_agent_harness.runner import collect, execute, gate, run_context, run_group


def test_absolute_from_import_and_valid_boundary() -> None:
    tree = ast.parse("from requests import Session")

    assert imports(tree, "acme.domain", False) == ("requests", "requests.Session")
    assert (
        boundaries([{"source": "acme.domain", "forbidden": ["requests"]}])[0].source
        == "acme.domain"
    )


def test_repository_root_is_not_an_implicit_source_inventory(project: Path) -> None:
    policy = project / ".harness/project.toml"
    policy.write_text(
        policy.read_text().replace('sources = ["src/acme"]', 'sources = ["."]'), encoding="utf-8"
    )

    with pytest.raises(HarnessError, match="explicit"):
        load(project)


def test_missing_edited_and_incomplete_generated_content(project: Path) -> None:
    assert ownership(project)[0].code == "render.missing"
    findings = audit_project(project, load(project))
    assert {item.code for item in findings} >= {
        "render.missing",
        "render.stale",
        "ci.gitlab_include",
    }

    apply(project, plan(project, load(project)))
    (project / ".harness/policy.md").write_text("edited", encoding="utf-8")
    assert "render.conflict" in {item.code for item in audit_project(project, load(project))}


@pytest.mark.parametrize("payload", ["[]", '{"files": []}'])
def test_ownership_manifest_shape_is_strict(project: Path, payload: str) -> None:
    (project / ".harness/manifest.json").write_text(payload, encoding="utf-8")
    with pytest.raises(HarnessError):
        ownership(project)


def test_github_only_audit_and_suppression_strings(project: Path) -> None:
    policy = project / ".harness/project.toml"
    policy.write_text(
        policy.read_text().replace('["github", "gitlab"]', '["github"]'), encoding="utf-8"
    )
    (project / "src/acme/__init__.py").write_text(
        'text = "# noqa"\n# ordinary comment\n', encoding="utf-8"
    )
    apply(project, plan(project, load(project)))

    assert suppressions(project, load(project)) == ()
    assert successful(audit_project(project, load(project)))


def test_extra_extension_inputs_participate_in_fingerprint(project: Path) -> None:
    directory = project / "rules/sub"
    directory.mkdir(parents=True)
    rule = directory / "custom.py"
    rule.write_text("value=1", encoding="utf-8")
    metadata = project / "pyproject.toml"
    metadata.write_text("[project]\nname='acme'\n", encoding="utf-8")
    spec = replace(load(project), inputs=("rules", "pyproject.toml"), tests=("absent",))
    before = fingerprint(project, spec)
    rule.write_text("value=2", encoding="utf-8")

    assert fingerprint(project, spec) != before
    with pytest.raises(HarnessError, match="Missing declared input"):
        fingerprint(project, replace(spec, inputs=("missing",)))


@pytest.mark.parametrize("previous", [BEGIN.encode(), END.encode()])
def test_partial_managed_markers_do_not_get_appended_over(previous: bytes) -> None:
    with pytest.raises(HarnessError):
        merge_block(previous, f"{BEGIN}\nrule\n{END}\n".encode())


def test_collector_requires_a_pipe(project: Path) -> None:
    with subprocess.Popen(
        [sys.executable, "-c", "pass"],
        stdout=subprocess.DEVNULL,
    ) as process:
        with pytest.raises(HarnessError, match="pipe"):
            collect(process, project / "log", time.monotonic() + 1, 1024)


def test_closed_stdout_does_not_remove_process_timeout(project: Path) -> None:
    command = Check(
        id="closed-pipe",
        group="static",
        argv=("@python", "-c", "import os; os.close(1); os.close(2)\nwhile True: pass"),
    )

    assert execute(project, command, 1024, timeout=0.2).detail == "timeout"


def test_ci_attempts_cannot_replay_old_evidence(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.delenv("CI_PIPELINE_ID", raising=False)
    assert run_context() == "local"
    monkeypatch.setenv("CI_PIPELINE_ID", "7")
    assert run_context() == "gitlab:7"
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    assert run_context() == "github:42:1"
    run_group(project, load(project), "static")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    assert gate(project, load(project))[0].status == "fail"


def test_test_gate_requires_all_coverage_findings(project: Path) -> None:
    spec = load(project)
    document = json.dumps(coverage_data())
    test = Check(
        id="behavior",
        group="tests",
        argv=(
            "@python",
            "-c",
            "from pathlib import Path; "
            + f"Path('.harness/reports/coverage.json').write_text({document!r})",
        ),
    )
    spec = replace(spec, checks=(spec.checks[0], test))
    run_group(project, spec, "static")
    run_group(project, spec, "tests")
    assert all(item.status == "pass" for item in gate(project, spec))
    report = project / ".harness/reports/tests.json"
    original = json.loads(report.read_text())
    for findings in (
        [],
        original["findings"][:2],
        [{**item, "status": "review"} for item in original["findings"]],
    ):
        report.write_text(json.dumps({**original, "findings": findings}), encoding="utf-8")
        assert gate(project, spec)[1].status == "fail"


def test_read_only_api_success_and_cli_doctor(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def query(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout='{"available": true}')

    monkeypatch.setattr(providers.subprocess, "run", query)
    assert providers.api(project, "github", "repos/owner/repo") == {"available": True}
    monkeypatch.setattr(
        cli,
        "doctor",
        lambda root, provider, repository: (
            Finding(code="ci", status="blocked", message="Not configured"),
        ),
    )
    assert (
        cli.main(
            ["--root", str(project), "doctor", "--provider", "github", "--repository", "owner/repo"]
        )
        == 1
    )


def test_coverage_cli_reports_observed_result(project: Path) -> None:
    directory = project / ".harness/reports"
    directory.mkdir()
    (directory / "coverage.json").write_text(json.dumps(coverage_data()), encoding="utf-8")

    assert cli.main(["--root", str(project), "coverage"]) == 0


@pytest.mark.parametrize("problem", ["wheel-development", "source-metadata", "source-generated"])
def test_built_archives_reject_leaked_or_missing_content(project: Path, problem: str) -> None:
    dist = project / "dist"
    dist.mkdir()
    with ZipFile(dist / "acme.whl", "w") as wheel:
        wheel.writestr("acme/__init__.py", "value=1")
        if problem == "wheel-development":
            wheel.writestr("tests/test_secret.py", "private")
    with tarfile.open(dist / "acme.tar.gz", "w:gz") as source:
        name = "acme/no-metadata" if problem == "source-metadata" else "acme/pyproject.toml"
        if problem == "source-generated":
            name = "acme/.venv/pyproject.toml"
        member = tarfile.TarInfo(name)
        member.size = 1
        source.addfile(member, io.BytesIO(b"x"))

    with pytest.raises(HarnessError):
        verify_package(project, "acme")
