"""Installed or standard-library modules must not substitute for built artifacts."""

import io
import subprocess
import tarfile
from pathlib import Path
from zipfile import ZipFile

import pytest

from python_agent_harness.package import verify_package


def test_isolated_import_must_originate_in_the_wheel(project: Path) -> None:
    directory = project / "dist"
    directory.mkdir()
    with ZipFile(directory / "example.whl", "w") as wheel:
        wheel.writestr("os.py", "artifact_marker = True\n")
    with tarfile.open(directory / "example.tar.gz", "w:gz") as source:
        metadata = tarfile.TarInfo("example/pyproject.toml")
        metadata.size = 1
        source.addfile(metadata, io.BytesIO(b"x"))

    with pytest.raises(subprocess.CalledProcessError) as failure:
        verify_package(project, "os")

    assert failure.value.returncode == 1
