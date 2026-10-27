"""Observable policy, syntax and dependency checks; semantic review stays explicit."""

import ast
import hashlib
import io
import json
import re
import tokenize
from pathlib import Path

from .model import Finding, Spec
from .paths import HarnessError, inside, source_files

MANIFEST = ".harness/manifest.json"


def digest(content: bytes) -> str:
    """Content identity used for ownership and execution evidence."""
    return hashlib.sha256(content).hexdigest()


def modules(root: Path, spec: Spec) -> dict[str, Path]:
    """Use source roots as Python package roots; support src and flat layouts."""
    result: dict[str, Path] = {}
    for source in spec.sources:
        base = inside(root, source)
        parent = base.parent if base.name != "src" else base
        for path in source_files(root, (source,)):
            pieces = list(path.relative_to(parent).with_suffix("").parts)
            if pieces[-1] == "__init__":
                pieces.pop()
            result[".".join(pieces)] = path
    return result


def imports(tree: ast.AST, module: str, package: bool) -> tuple[str, ...]:
    """Resolve static relative imports; dynamic import semantics require review."""
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = module.split(".") if package else module.split(".")[:-1]
            if node.level:
                prefix = prefix[: len(prefix) - node.level + 1]
                name = ".".join((*prefix, node.module or "")).rstrip(".")
            else:
                name = node.module or ""
            result.extend((name, *(f"{name}.{alias.name}" for alias in node.names)))
    return tuple(result)


def matches(module: str, prefix: str) -> bool:
    """A module prefix does not match an unrelated similarly named package."""
    return module == prefix or module.startswith(prefix + ".")


def dependency_graph(root: Path, spec: Spec) -> dict[str, tuple[str, ...]]:
    """Build an import graph without importing user code."""
    return {
        name: imports(
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path)),
            name,
            path.name == "__init__.py",
        )
        for name, path in modules(root, spec).items()
    }


def reachable(graph: dict[str, tuple[str, ...]], start: str) -> set[str]:
    """Follow local helpers transitively, with cycle protection."""
    visited: set[str] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        for target in graph.get(current, ()):
            if target not in visited:
                visited.add(target)
                pending.append(target)
    return visited


def forbidden_dependencies(
    graph: dict[str, tuple[str, ...]], start: str, prefixes: tuple[str, ...]
) -> tuple[str, ...]:
    """Query forbidden transitive targets, preserving deterministic diagnostic order."""
    return tuple(
        target
        for target in sorted(reachable(graph, start))
        if any(matches(target, prefix) for prefix in prefixes)
    )


def architecture(root: Path, spec: Spec) -> tuple[Finding, ...]:
    """Check declared forbidden edges, including static transitive dependencies."""
    graph = dependency_graph(root, spec)
    findings: list[Finding] = []
    for boundary in spec.boundaries:
        selected = [name for name in graph if matches(name, boundary.source)]
        if not selected:
            findings.append(
                Finding(
                    code="architecture.source",
                    status="fail",
                    message=f"No modules match {boundary.source}",
                )
            )
        for name in selected:
            findings.extend(
                Finding(
                    code="architecture.import",
                    status="fail",
                    message=f"{name} depends on forbidden {target}",
                )
                for target in forbidden_dependencies(graph, name, boundary.forbidden)
            )
    return tuple(findings)


def artifact_drift(root: Path, records: dict[str, object]) -> tuple[Finding, ...]:
    """Compare manifest records with files and managed blocks without writing."""
    from .render import block_content

    findings: list[Finding] = []
    for name, expected in records.items():
        path = inside(root, name)
        if not isinstance(expected, dict) or set(expected) != {"hash", "block"}:
            raise HarnessError("Invalid manifest record")
        content = path.read_bytes() if path.is_file() else b""
        if expected["block"] and content:
            content = block_content(content)
        if not path.is_file() or digest(content) != expected["hash"]:
            findings.append(
                Finding(
                    code="render.drift",
                    status="fail",
                    message="Generated content changed; review and render an update",
                    path=name,
                )
            )
    return tuple(findings)


def ownership(root: Path) -> tuple[Finding, ...]:
    """Detect edited generated files and policy changes since last rendering."""
    manifest = inside(root, MANIFEST)
    if not manifest.exists():
        return (
            Finding(code="render.missing", status="fail", message="Run render and review its diff"),
        )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise HarnessError("Invalid ownership manifest")
    findings = list(artifact_drift(root, data["files"]))
    policy = inside(root, ".harness/project.toml")
    if data.get("policy") != digest(policy.read_bytes()):
        findings.append(
            Finding(
                code="policy.changed",
                status="fail",
                message="Policy changed since rendering; review the policy diff explicitly",
            )
        )
    return tuple(findings)


def evidence(root: Path, spec: Spec) -> tuple[Finding, ...]:
    """Verify evidence exists without claiming that a filename proves its quality."""
    findings: list[Finding] = []
    for rule in spec.requirements:
        if rule.enforcement == "review":
            findings.append(
                Finding(
                    code="requirement.review",
                    status="review",
                    message=f"{rule.id}: {rule.description}",
                )
            )
        for name in rule.evidence:
            if not inside(root, name).is_file():
                findings.append(
                    Finding(
                        code="requirement.evidence",
                        status="fail",
                        message=f"Missing evidence for {rule.id}",
                        path=name,
                    )
                )
    return tuple(findings)


def suppressions(root: Path, spec: Spec) -> tuple[Finding, ...]:
    """Flag unqualified or unexplained common suppressions in production and tests."""
    found: list[Finding] = []
    roots = (*spec.sources, *(name for name in spec.tests if inside(root, name).exists()))
    for path in source_files(root, roots):
        tokens = tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            index, line = token.start[0], token.string
            if re.search(r"#\s*(?:noqa|type:\s*ignore|pragma:\s*no cover)", line) and not re.search(
                r"(?:noqa:\s*[A-Z][A-Z0-9, ]*|type:\s*ignore\[[^]]+\]|pragma:\s*no cover)\s+-\s*\S",
                line,
            ):
                found.append(
                    Finding(
                        code="suppression.reason",
                        status="fail",
                        message=f"Line {index}: suppression needs a specific rule and explanation",
                        path=path.relative_to(root).as_posix(),
                    )
                )
    return tuple(found)


def audit_project(root: Path, spec: Spec) -> tuple[Finding, ...]:
    """Combine independent diagnostics; never import production to inspect it."""
    from .render import plan

    findings = (
        *ownership(root),
        *evidence(root, spec),
        *architecture(root, spec),
        *suppressions(root, spec),
    )
    try:
        if plan(root, spec):
            findings += (
                Finding(
                    code="render.stale",
                    status="fail",
                    message="Generated output is incomplete or stale",
                ),
            )
    except HarnessError as error:
        findings += (Finding(code="render.conflict", status="fail", message=str(error)),)
    if "gitlab" in spec.providers:
        path = inside(root, ".gitlab-ci.yml")
        included = path.is_file() and any(
            re.fullmatch(r"\s*-?\s*local:\s*['\"]?\.harness/gitlab-ci.yml['\"]?\s*", line)
            for line in path.read_text(encoding="utf-8").splitlines()
        )
        if not included:
            findings += (
                Finding(
                    code="ci.gitlab_include",
                    status="blocked",
                    message="Add the harness GitLab include and verify the compiled pipeline jobs",
                ),
            )
        configured = path.is_file() and any(
            "if:" in line and "CI_PIPELINE_SOURCE" in line and "merge_request_event" in line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        if not configured:
            findings += (
                Finding(
                    code="ci.gitlab_mr",
                    status="blocked",
                    message="Declare merge-request workflow/job rules directly in .gitlab-ci.yml",
                ),
            )
    return findings


def declared_inputs(root: Path, names: tuple[str, ...]) -> set[Path]:
    """Inventory required evidence/extensions, rejecting missing and escaping paths."""
    paths: set[Path] = set()
    for name in names:
        path = inside(root, name)
        if not path.exists():
            raise HarnessError(f"Missing declared input: {name}")
        for candidate in path.rglob("*") if path.is_dir() else (path,):
            checked = inside(root, candidate.relative_to(root).as_posix())
            if checked.is_file():
                paths.add(checked)
    return paths


def fingerprint(root: Path, spec: Spec) -> str:
    """Bind a command report to policy, source, tests and the current runner."""
    paths = set(source_files(root, spec.sources))
    extras = (*spec.inputs, *(name for rule in spec.requirements for name in rule.evidence))
    paths.update(declared_inputs(root, extras))
    for name in spec.tests:
        if inside(root, name).exists():
            paths.update(source_files(root, (name,)))
    paths.update(
        inside(root, name)
        for name in (".harness/project.toml", ".harness/manifest.json", ".harness/runner.pyz")
        if inside(root, name).exists()
    )
    for name in ("pyproject.toml", "uv.lock", "poetry.lock", "requirements.txt"):
        if inside(root, name).is_file():
            paths.add(inside(root, name))
    content = "\n".join(
        f"{path.relative_to(root).as_posix()}:{digest(path.read_bytes())}" for path in sorted(paths)
    )
    return digest(content.encode())
