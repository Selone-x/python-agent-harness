"""Negative integration and boundary cases that must never silently pass."""

import io
import json
import runpy
import subprocess
import sys
import tarfile
from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile

import pytest
from conftest import BASE
from test_audit_coverage import coverage_data, write_coverage

from python_agent_harness import cli, providers
from python_agent_harness.audit import evidence, ownership, suppressions
from python_agent_harness.bootstrap import initialize
from python_agent_harness.config import load, parse
from python_agent_harness.coverage import counters, verify_coverage
from python_agent_harness.model import Check, Requirement
from python_agent_harness.package import verify_package
from python_agent_harness.paths import HarnessError, source_files
from python_agent_harness.render import BEGIN, END, apply, plan
from python_agent_harness.runner import run_group, run_setup


def test_main_module_and_successful_package_dispatch(
    monkeypatch: pytest.MonkeyPatch, project: Path
) -> None:
    monkeypatch.setattr(sys, "argv", ["harness", "--version"])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("python_agent_harness", run_name="__main__")
    assert exit_info.value.code == 0

    monkeypatch.setattr(cli, "verify_package", lambda root, module: None)
    assert cli.main(["--root", str(project), "package", "--module", "acme"]) == 0


def test_invalid_kind_boundary_budget_and_duplicate_requirements(project: Path) -> None:
    import tomllib

    base = tomllib.loads(BASE)
    for changed in (
        {**base, "kind": "unknown"},
        {**base, "boundaries": "bad"},
        {**base, "requirements": base["requirements"] * 2},
    ):
        with pytest.raises(HarnessError):
            parse(changed)
    for value in (None, [], "wrong"):
        with pytest.raises(HarnessError):
            counters(value)


def test_library_missing_package_and_unsafe_check_id(project: Path) -> None:
    policy = project / ".harness/project.toml"
    policy.write_text(BASE.replace('kind = "service"', 'kind = "library"'), encoding="utf-8")
    with pytest.raises(HarnessError, match="package"):
        load(project)
    policy.write_text(BASE.replace('id = "format"', 'id = "../escape"'), encoding="utf-8")
    with pytest.raises(HarnessError, match="identifier"):
        load(project)


@pytest.mark.parametrize("bad", ["external", "duplicate", "entry", "total"])
def test_coverage_inventory_and_totals_are_not_trusted(project: Path, bad: str) -> None:
    document = coverage_data()
    summary = {"covered_lines": 1, "num_statements": 1, "covered_branches": 0, "num_branches": 0}
    if bad == "external":
        document["files"] = {"/outside/source.py": {"summary": summary}}
    elif bad == "duplicate":
        document["files"] = {
            "src/acme/__init__.py": {"summary": summary},
            "./src/acme/__init__.py": {"summary": summary},
        }
    elif bad == "entry":
        document["files"] = {"src/acme/__init__.py": []}
    else:
        document["totals"] = {**summary, "num_statements": 2}
    write_coverage(project, document)

    with pytest.raises(HarnessError):
        verify_coverage(project, load(project))


def test_non_python_files_are_not_coverage_sources(project: Path) -> None:
    (project / "src/acme/readme.txt").write_text("text", encoding="utf-8")

    assert source_files(project, ("src/acme/readme.txt",)) == ()


def test_present_evidence_and_missing_test_root(project: Path) -> None:
    (project / "tests/rule.py").write_text("value = 1", encoding="utf-8")
    requirement = Requirement(
        id="r",
        description="An explicit rule",
        enforcement="test",
        check="behavior",
        evidence=("tests/rule.py",),
    )

    assert evidence(project, replace(load(project), requirements=(requirement,))) == ()
    assert suppressions(project, replace(load(project), tests=("absent",))) == ()


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        '{"files": []}',
        '{"files": {"x": null}}',
        '{"files": {"x": {"hash": 3, "block": false}}}',
    ],
)
def test_invalid_manifest_cannot_authorize_writes(project: Path, payload: str) -> None:
    (project / ".harness/manifest.json").write_text(payload, encoding="utf-8")

    with pytest.raises(HarnessError):
        plan(project, load(project))


def test_missing_owned_file_and_invalid_owned_record(project: Path) -> None:
    apply(project, plan(project, load(project)))
    (project / ".harness/policy.md").unlink()
    assert ownership(project)[0].code == "render.drift"
    manifest = project / ".harness/manifest.json"
    manifest.write_text('{"files":{"x": "not-a-record"}}', encoding="utf-8")
    with pytest.raises(HarnessError):
        ownership(project)


def test_unowned_managed_markers_are_a_conflict(project: Path) -> None:
    (project / "AGENTS.md").write_text(f"{BEGIN}\nold\n{END}\n", encoding="utf-8")

    with pytest.raises(HarnessError, match="Unowned"):
        plan(project, load(project))


def test_temporary_output_conflict_and_empty_scaffold_guards(project: Path, tmp_path: Path) -> None:
    (project / "new.harness-new").write_text("preserve", encoding="utf-8")
    with pytest.raises(HarnessError, match="Temporary"):
        apply(project, {"new": b"value"})
    empty = tmp_path / "nonempty"
    empty.mkdir()
    (empty / "owned.py").write_text("value=1", encoding="utf-8")
    with pytest.raises(HarnessError, match="empty"):
        initialize(empty, "demo", "demo", "service", ("github",), True)


def test_deep_budget_and_input_mutation_are_failures(project: Path) -> None:
    spec = load(project)
    deep = (
        Check(id="slow", group="deep", argv=("@python", "-c", "while True: pass"), timeout=2),
        Check(id="next", group="deep", argv=("@python", "-c", "pass")),
    )
    report = run_group(project, replace(spec, checks=(*spec.checks, *deep), deep_budget=1), "deep")
    assert report["status"] == "fail"
    assert "deep budget exhausted" in str(report["checks"])

    command = Check(
        id="edit",
        group="static",
        argv=(
            "@python",
            "-c",
            "from pathlib import Path; Path('src/acme/__init__.py').write_text('value = 2')",
        ),
    )
    assert (
        run_group(project, replace(spec, checks=(command, *spec.checks[1:])), "static")[
            "inputs_unchanged"
        ]
        is False
    )


def test_successful_setup_and_fresh_coverage(project: Path) -> None:
    spec = load(project)
    assert run_setup(project, replace(spec, setup=(("@python", "-c", "pass"),)))[0].status == "pass"
    document = json.dumps(coverage_data())
    command = Check(
        id="behavior",
        group="tests",
        argv=(
            "@python",
            "-c",
            "from pathlib import Path; "
            f"Path('.harness/reports/coverage.json').write_text({document!r})",
        ),
    )

    assert (
        run_group(project, replace(spec, checks=(spec.checks[0], command)), "tests")["status"]
        == "pass"
    )


def test_package_archive_and_isolated_wheel_import(project: Path) -> None:
    distribution = project / "dist"
    distribution.mkdir()
    with ZipFile(distribution / "acme-1.0-py3-none-any.whl", "w") as wheel:
        wheel.writestr("acme/__init__.py", "value = 1\n")
    with tarfile.open(distribution / "acme-1.0.tar.gz", "w:gz") as source:
        content = b"[project]\nname='acme'\n"
        member = tarfile.TarInfo("acme-1.0/pyproject.toml")
        member.size = len(content)
        source.addfile(member, io.BytesIO(content))

    verify_package(project, "acme")
    with pytest.raises(HarnessError, match="Invalid import"):
        verify_package(project, "acme;exit()")
    with pytest.raises(HarnessError, match="absent"):
        verify_package(project, "absent")


def test_provider_api_never_echoes_credentials(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def denied(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="private token", stderr="private token")

    monkeypatch.setattr(providers.subprocess, "run", denied)
    with pytest.raises(HarnessError) as failure:
        providers.api(project, "github", "repos/example/project")
    assert "private token" not in str(failure.value)

    def unavailable(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("private token")

    monkeypatch.setattr(providers.subprocess, "run", unavailable)
    with pytest.raises(HarnessError, match="FileNotFoundError"):
        providers.api(project, "gitlab", "projects/1")


def test_read_only_provider_queries_and_unavailable_approvals(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested: list[str] = []

    def query(root: Path, provider: str, endpoint: str) -> object:
        requested.append(endpoint)
        if endpoint.endswith("/protection"):
            return {}
        if "protected_branches" in endpoint:
            return []
        if endpoint.endswith("/approvals"):
            raise HarnessError("not available")
        return {"default_branch": "main"}

    monkeypatch.setattr(providers, "api", query)
    assert all(
        item.status == "blocked" for item in providers.doctor(project, "github", "owner/repo")
    )
    assert providers.doctor(project, "gitlab", "group/project")[0].status == "blocked"
    assert "projects/group%2Fproject" in requested
    with pytest.raises(HarnessError):
        providers.doctor(project, "github", "../escape")


def test_provider_parse_invalid_metadata_and_pagination(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(providers, "api", lambda root, provider, endpoint: None)
    with pytest.raises(HarnessError, match="metadata"):
        providers.doctor(project, "github", "owner/repo")
    monkeypatch.setattr(providers, "api", lambda root, provider, endpoint: [{}] * 100)
    with pytest.raises(HarnessError, match="pages"):
        providers.doctor(project, "gitlab", "group/project")
