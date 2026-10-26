"""Constrain discovery and generated writes to the selected project."""

from pathlib import Path, PurePosixPath


class HarnessError(ValueError):
    """An expected configuration or project-state problem at the CLI boundary."""


def inside(root: Path, relative: str) -> Path:
    """Reject absolute paths, traversal and symlink escapes."""
    path = PurePosixPath(relative)
    if not relative or path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise HarnessError(f"Expected a project-relative path: {relative!r}")
    result = root.joinpath(*path.parts)
    if not result.resolve().is_relative_to(root.resolve()):
        raise HarnessError(f"Path escapes the project: {relative}")
    return result


def source_files(root: Path, sources: tuple[str, ...]) -> tuple[Path, ...]:
    """Include every Python file, including files not imported by any test."""
    found: set[Path] = set()
    for source in sources:
        path = inside(root, source)
        if not path.exists():
            raise HarnessError(f"Source does not exist: {source}")
        candidates = (path,) if path.is_file() else path.rglob("*.py")
        for candidate in candidates:
            relative = candidate.relative_to(root).as_posix()
            checked = inside(root, relative)
            if checked.suffix == ".py":
                found.add(checked)
    return tuple(sorted(found))
