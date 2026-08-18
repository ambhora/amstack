# SPDX-License-Identifier: Apache-2.0
import os

from spack_repo.builtin.build_systems.generic import Package
from spack.package import *


class Properdocs(Package):
    """ProperDocs + MaterialX command-line frontend."""

    homepage = "https://properdocs.org/"
    has_code = False

    version("1.6.7")

    depends_on("python@3.10:", type=("build", "run"))
    depends_on("py-pip", type="build")

    def install(self, spec, prefix):
        site = join_path(prefix, "lib", "properdocs")
        mkdirp(site)
        mkdirp(prefix.bin)

        pip = Executable(join_path(spec["py-pip"].prefix.bin, "pip"))
        pip(
            "install",
            "--disable-pip-version-check",
            "--no-compile",
            "--target",
            site,
            f"properdocs=={spec.version}",
            "mkdocs-materialx==10.2.0",
        )

        python = join_path(spec["python"].prefix.bin, "python3")
        launcher = join_path(prefix.bin, "properdocs")
        with open(launcher, "w", encoding="utf-8") as stream:
            stream.write(f"#!{python}\n")
            stream.write("import sys\n")
            stream.write(f"sys.path.insert(0, {site!r})\n")
            stream.write("from properdocs.__main__ import cli\n")
            stream.write("cli()\n")
        os.chmod(launcher, 0o755)
