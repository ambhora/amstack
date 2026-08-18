# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from amstack.analyse import analyse_repository
from amstack.config import Repository


def _write_project(root: Path) -> None:
    (root / "CMakeLists.txt").write_text(
        """
project(nola VERSION 1.2.3 LANGUAGES NONE)

besa_features_add(
  FEATURES
  build-source
  toolchain-cpp
  toolchain-cuda
  extra-widget
)

besa_features_default(
  FEATURES
  build-source
  toolchain-cpp
)

besa_dependency_add(
  NAME fmt
  VERSION 11
  KIND NORMAL
  PROVIDER CMAKE
  WHEN ALL_OF extra-widget
)

besa_dependency_add(
  NAME Threads
  KIND NORMAL
  PROVIDER CMAKE
)
""",
        encoding="utf-8",
    )
    package = root / "spack/spack_repo/nola_dev/packages/nola_dev_env/package.py"
    package.parent.mkdir(parents=True)
    package.write_text(
        """
from spack_repo.builtin.build_systems.bundle import BundlePackage
from spack.package import *

class NolaDevEnv(BundlePackage):
    version("1")
    variant("cuda", default=False, description="CUDA")
    depends_on("cmake")
    depends_on("fmt@11:")
    depends_on("cuda", when="+cuda")
""",
        encoding="utf-8",
    )


def test_analyse_besa_project(tmp_path: Path) -> None:
    _write_project(tmp_path)
    model = analyse_repository(
        tmp_path,
        Repository(url="https://github.com/ambhora/nola.git", name="nola"),
    )

    assert model.version == "1.2.3"
    assert model.features == (
        "build-source",
        "toolchain-cpp",
        "toolchain-cuda",
        "extra-widget",
    )
    assert model.default_features == frozenset({"build-source", "toolchain-cpp"})
    assert model.dependencies[0].name == "fmt"
    assert model.dev_dependencies[1].name == "fmt"
