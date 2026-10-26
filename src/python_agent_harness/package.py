"""Check built distributions and smoke-import the actual wheel."""

import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from .paths import HarnessError, inside


def verify_package(root: Path, module: str) -> None:
    """Use an isolated interpreter outside the source tree, with bounded execution."""
    if not re.fullmatch(r"[A-Za-z_]\w*(\.[A-Za-z_]\w*)*", module):
        raise HarnessError("Invalid import module")
    distribution = inside(root, "dist")
    wheels = list(distribution.glob("*.whl"))
    sources = list(distribution.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise HarnessError("Expected exactly one wheel and one source distribution")
    with ZipFile(wheels[0]) as wheel:
        names = wheel.namelist()
    module_path = module.replace(".", "/")
    if not any(name in names for name in (module_path + ".py", module_path + "/__init__.py")):
        raise HarnessError("Requested import module is absent from wheel")
    if any(
        PurePosixPath(name).parts[0] in {"tests", ".harness", ".venv", "tools"} for name in names
    ):
        raise HarnessError("Development content leaked into wheel")
    with tarfile.open(sources[0]) as source:
        members = source.getnames()
    if not any(name.endswith("/pyproject.toml") for name in members) or any(
        {".venv", ".harness", ".reports", ".uv-cache"}.intersection(PurePosixPath(name).parts)
        for name in members
    ):
        raise HarnessError("Source distribution lacks build metadata or contains generated content")
    temporary_root = inside(root, ".harness/reports")
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
        subprocess.run(  # noqa: S603 - fixed isolated interpreter, validated module and local wheel.
            [
                sys.executable,
                "-I",
                "-c",
                "import importlib,sys; sys.path.insert(0,sys.argv[1]); "
                "module=importlib.import_module(sys.argv[2]); "
                "assert module.__file__.startswith(sys.argv[1] + '/')",
                str(wheels[0].resolve()),
                module,
            ],
            cwd=temporary,
            check=True,
            timeout=30,
        )
