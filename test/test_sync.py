# SPDX-License-Identifier: Apache-2.0

import subprocess
from pathlib import Path

from amstack.config import Repository
from amstack.sync import sync_repository


def _git(repository: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write_project(source: Path) -> None:
    (source / "CMakeLists.txt").write_text(
        """
project(nola VERSION 0.2.0 LANGUAGES NONE)
besa_features_add(FEATURES build-source toolchain-cpp)
besa_features_default(FEATURES build-source toolchain-cpp)
""",
        encoding="utf-8",
    )
    dev = source / "spack/spack_repo/nola_dev/packages/nola_dev_env/package.py"
    dev.parent.mkdir(parents=True)
    dev.write_text(
        """
from spack_repo.builtin.build_systems.bundle import BundlePackage
from spack.package import *
class NolaDevEnv(BundlePackage):
    version("1")
    depends_on("cmake")
""",
        encoding="utf-8",
    )


def test_sync_discovers_tags_and_configured_branches(tmp_path: Path) -> None:
    source = tmp_path / "nola"
    source.mkdir()
    _write_project(source)

    _git(source, "init", "-q", "-b", "main")
    _git(source, "config", "user.email", "test@example.com")
    _git(source, "config", "user.name", "Test")
    _git(source, "add", ".")
    _git(source, "commit", "-qm", "initial")
    _git(source, "tag", "v0.1.0")
    tag_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()

    _git(source, "checkout", "-qb", "develop")
    (source / "README.md").write_text("development\n", encoding="utf-8")
    _git(source, "add", "README.md")
    _git(source, "commit", "-qm", "develop")
    _git(source, "checkout", "-q", "main")

    amstack = tmp_path / "amstack"
    repository = Repository(url=str(source), name="nola", branches=("main", "develop"))
    result = sync_repository(repository, amstack)

    destination = amstack / "spack_repo/amstack/packages/nola/package.py"
    recipe = destination.read_text(encoding="utf-8")
    assert result.package == "nola"
    assert result.changed is True
    assert "class Nola(AmbhoraCMakePackage):" in recipe
    assert 'version("main", branch="main")' in recipe
    assert 'version("develop", branch="develop")' in recipe
    assert f'version("0.1.0", tag="v0.1.0", commit="{tag_commit}")' in recipe

    second = sync_repository(repository, amstack)
    assert second.changed is False


def test_sync_dry_run_shows_changes_without_writing(tmp_path: Path) -> None:
    source = tmp_path / "nola"
    source.mkdir()
    _write_project(source)

    _git(source, "init", "-q", "-b", "main")
    _git(source, "config", "user.email", "test@example.com")
    _git(source, "config", "user.name", "Test")
    _git(source, "add", ".")
    _git(source, "commit", "-qm", "initial")

    amstack = tmp_path / "amstack"
    repository = Repository(url=str(source), name="nola", branches=("main",))
    result = sync_repository(repository, amstack, dry_run=True)

    destination = amstack / "spack_repo/amstack/packages/nola/package.py"
    assert result.changed is True
    assert destination.exists() is False
    assert "--- /dev/null" in result.diff
    assert "+++ b/spack_repo/amstack/packages/nola/package.py" in result.diff
    assert "+class Nola(AmbhoraCMakePackage):" in result.diff
