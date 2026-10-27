"""Deterministic, owned output with conflict detection before the first write."""

import io
import json
from dataclasses import dataclass
from difflib import unified_diff
from importlib.resources import files
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from . import __version__
from .audit import MANIFEST, digest
from .config import SPEC_PATH
from .model import Spec
from .paths import HarnessError, inside
from .providers import github_workflow, gitlab_workflow

BEGIN = "<!-- python-agent-harness:begin -->"
END = "<!-- python-agent-harness:end -->"


@dataclass(frozen=True, slots=True, kw_only=True)
class Artifact:
    """A fully owned file, or an owned block in a user's instructions."""

    path: str
    content: bytes
    block: bool = False


def runner_bundle() -> bytes:
    """Bundle the stdlib-only runtime; a PyPI publication is not a prerequisite."""
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        entries = {
            "__main__.py": b"from python_agent_harness.cli import main\nraise SystemExit(main())\n"
        }
        for item in files("python_agent_harness").iterdir():
            if item.name.endswith(".py"):
                entries[f"python_agent_harness/{item.name}"] = item.read_bytes()
        for name, content in sorted(entries.items()):
            info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return output.getvalue()


def policy_document(spec: Spec) -> str:
    """Make enforcement limits visible without pretending prose is an executable rule."""
    lines = [f"# {spec.name}: harness policy", "", spec.description, "", "Requirements:"]
    lines.extend(
        f"- {rule.id} [{rule.enforcement}]: {rule.description}" for rule in spec.requirements
    )
    lines.extend(
        (
            "",
            f"Coverage: lines >= {spec.line_minimum}%; branches >= {spec.branch_minimum}%.",
            "Source inventory: " + ", ".join(spec.sources),
            "",
            "Static imports are checked transitively. Runtime wiring requires tests/review.",
            "Evidence paths establish traceability, not assertion quality.",
            "Mutation and benchmarks run only in the explicitly configured bounded deep group.",
            "",
            "Do not commit or push directly to the main branch. Use a PR/MR with a short summary.",
            "Do not weaken checks, suppressions, thresholds or expected values for green.",
            "Policy/CI changes need separate review. Verify actual platform protection.",
            "Use independent expected values and test relevant errors, boundaries and invariants.",
            "",
        )
    )
    return "\n".join(lines)


def artifacts(spec: Spec) -> tuple[Artifact, ...]:
    """Generate common outputs plus the selected provider integrations."""
    instructions = (
        f"{BEGIN}\nRead `.harness/policy.md` and `.harness/project.toml`.\n"
        "Use `just check` for the same bounded groups and gate as CI.\n"
        "The stdlib runner may use standalone Python for bootstrap before tool setup.\n"
        f"Keep existing guidelines. Policy/CI changes need explicit review.\n{END}\n"
    )
    result = [
        Artifact(path=".harness/runner.pyz", content=runner_bundle()),
        Artifact(path=".harness/policy.md", content=policy_document(spec).encode()),
        Artifact(path="AGENTS.md", content=instructions.encode(), block=True),
        Artifact(
            path="CLAUDE.md",
            content=f"{BEGIN}\nFollow AGENTS.md and .harness/policy.md.\n{END}\n".encode(),
            block=True,
        ),
        Artifact(
            path=".harness/pre-commit-config.yaml",
            content=b"""repos:
  - repo: local
    hooks:
      - id: harness-static
        name: Harness static checks
        entry: python3 -I .harness/runner.pyz check --group static
        language: system
        pass_filenames: false
        always_run: true
""",
        ),
    ]
    if "github" in spec.providers:
        result.append(
            Artifact(path=".github/workflows/harness.yml", content=github_workflow(spec).encode())
        )
    if "gitlab" in spec.providers:
        result.append(
            Artifact(path=".harness/gitlab-ci.yml", content=gitlab_workflow(spec).encode())
        )
    return tuple(result)


def block_content(content: bytes) -> bytes:
    """Only the managed instruction block participates in ownership checks."""
    text = content.decode("utf-8")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise HarnessError("Managed instruction markers are missing or duplicated")
    start = text.index(BEGIN)
    finish = text.index(END) + len(END)
    if start > finish:
        raise HarnessError("Managed instruction markers are reversed")
    return text[start:finish].encode()


def merge_block(previous: bytes, wanted: bytes) -> bytes:
    """Preserve all existing instructions outside the owned block."""
    if BEGIN.encode() not in previous and END.encode() not in previous:
        return previous.rstrip() + (b"\n\n" if previous.strip() else b"") + wanted
    owned = block_content(previous)
    return previous.replace(owned, block_content(wanted), 1)


def previous_manifest(root: Path) -> dict[str, dict[str, object]]:
    """Unknown manifest shapes cannot authorize overwrites."""
    path = inside(root, MANIFEST)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("files") if isinstance(data, dict) else None
    if not isinstance(records, dict) or any(
        not isinstance(item, dict)
        or set(item) != {"hash", "block"}
        or not isinstance(item["hash"], str)
        or type(item["block"]) is not bool
        for item in records.values()
    ):
        raise HarnessError("Invalid ownership manifest")
    return records


def prepare_artifact(
    path: Path, artifact: Artifact, expected: dict[str, object] | None
) -> tuple[bytes, bytes]:
    """Validate one artifact's ownership and compute its update without writes."""
    old = path.read_bytes() if path.exists() else b""
    actual = block_content(old) if expected and expected["block"] else old
    if expected and digest(actual) != expected["hash"]:
        raise HarnessError(f"Conflict in edited generated content: {artifact.path}")
    if path.exists() and not expected and not artifact.block and old != artifact.content:
        raise HarnessError(f"Refusing to overwrite unowned file: {artifact.path}")
    if artifact.block and not expected and (BEGIN.encode() in old or END.encode() in old):
        raise HarnessError(f"Unowned managed block: {artifact.path}")
    content = merge_block(old, artifact.content) if artifact.block else artifact.content
    return old, content


def plan(root: Path, spec: Spec) -> dict[str, bytes]:
    """Calculate every update and conflict without changing the working tree."""
    previous = previous_manifest(root)
    outputs = list(artifacts(spec))
    gitlab = inside(root, ".gitlab-ci.yml")
    if "gitlab" in spec.providers and (not gitlab.exists() or ".gitlab-ci.yml" in previous):
        outputs.append(
            Artifact(
                path=".gitlab-ci.yml",
                content=b"""workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - if: '$CI_PIPELINE_SOURCE == "web"'
include:
  - local: .harness/gitlab-ci.yml
""",
            )
        )
    changes: dict[str, bytes] = {}
    records: dict[str, dict[str, object]] = {}
    for artifact in outputs:
        path = inside(root, artifact.path)
        old, content = prepare_artifact(path, artifact, previous.get(artifact.path))
        owned = block_content(content) if artifact.block else content
        records[artifact.path] = {"hash": digest(owned), "block": artifact.block}
        if content != old or not path.exists():
            changes[artifact.path] = content
    removed = previous.keys() - records.keys()
    if removed:
        raise HarnessError(f"Provider/output removal needs manual review: {sorted(removed)}")
    manifest = {
        "schema_version": 1,
        "version": __version__,
        "policy": digest(inside(root, SPEC_PATH).read_bytes()),
        "files": records,
    }
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    manifest_path = inside(root, MANIFEST)
    if not manifest_path.exists() or manifest_path.read_bytes() != encoded:
        changes[MANIFEST] = encoded
    return changes


def describe(root: Path, changes: dict[str, bytes]) -> list[dict[str, object]]:
    """Expose reviewable text diffs and binary content identities before applying."""
    result: list[dict[str, object]] = []
    for name, content in changes.items():
        path = inside(root, name)
        old = path.read_bytes() if path.exists() else b""
        difference = None
        if path.suffix != ".pyz":
            difference = "".join(
                unified_diff(
                    old.decode("utf-8").splitlines(keepends=True),
                    content.decode("utf-8").splitlines(keepends=True),
                    fromfile=f"a/{name}",
                    tofile=f"b/{name}",
                )
            )
        result.append(
            {"path": name, "bytes": len(content), "sha256": digest(content), "diff": difference}
        )
    return result


def apply(root: Path, changes: dict[str, bytes]) -> None:
    """Validate all destinations first; write only already reviewed generated outputs."""
    targets = [(inside(root, name), content) for name, content in changes.items()]
    for path, _ in targets:
        temporary = path.with_name(path.name + ".harness-new")
        if temporary.exists() or temporary.is_symlink():
            raise HarnessError(f"Temporary output already exists: {temporary.name}")
    for path, content in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".harness-new")
        temporary.write_bytes(content)
        temporary.replace(path)
