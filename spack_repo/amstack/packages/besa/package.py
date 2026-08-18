# SPDX-License-Identifier: Apache-2.0

from spack_repo.builtin.build_systems.python import PythonPackage
from spack.package import *


class Besa(PythonPackage):
    """Declarative project-development tooling for CMake and Python projects."""

    homepage = "https://github.com/ambhora/besa"
    pypi = "besa/besa-0.1.0.tar.gz"
    git = "https://github.com/ambhora/besa.git"

    license("Apache-2.0")

    version("main", branch="main", preferred=True)

    version(
        "0.1.0",
        sha256="7a8c0c1970050c90a58f1e8c97d67cd46e2dd691cda34f09a36a9baeffd5b29b",
    )

    depends_on("python@3.11:", type=("build", "run"))
    depends_on("py-hatchling", type="build")
