# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from amstack.config import load_repositories


def test_repository_defaults(tmp_path: Path) -> None:
    config = tmp_path / "amstack.yaml"
    config.write_text(
        "repositories:\n  - url: https://github.com/ambhora/nola.git\n",
        encoding="utf-8",
    )

    repositories = load_repositories(config)

    assert repositories[0].name == "nola"
    assert repositories[0].branches == ("main",)
    assert repositories[0].dev_environment_package == "nola-dev-env"


def test_repository_additional_branches_extend_main(tmp_path: Path) -> None:
    config = tmp_path / "amstack.yaml"
    config.write_text(
        """
repositories:
  - url: https://github.com/ambhora/nola.git
    branches:
      - develop
      - release/next
      - main
""",
        encoding="utf-8",
    )

    repositories = load_repositories(config)

    assert repositories[0].branches == ("main", "develop", "release/next")
