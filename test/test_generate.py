# SPDX-License-Identifier: Apache-2.0

from amstack.generate import render_package
from amstack.model import BesaDependency, DevDependency, GitBranch, GitTag, ProjectModel


def test_render_creates_new_installable_package() -> None:
    model = ProjectModel(
        name="nola",
        version="1.2.3",
        url="https://github.com/ambhora/nola.git",
        branches=(
            GitBranch("main", "main"),
            GitBranch("release-next", "release/next"),
        ),
        tags=(
            GitTag("1.2.3", "v1.2.3", "a" * 40),
            GitTag("1.2.2", "1.2.2", "b" * 40),
        ),
        features=("build-source", "toolchain-cpp", "extra-widget"),
        default_features=frozenset({"build-source", "toolchain-cpp"}),
        dependencies=(
            BesaDependency("fmt", "11", "NORMAL", ("extra-widget",)),
            BesaDependency("Threads", None, "NORMAL", ()),
        ),
        dev_variants=(),
        dev_dependencies=(DevDependency("fmt@11:", None),),
    )

    recipe = render_package(model)

    assert "class Nola(AmbhoraCMakePackage):" in recipe
    assert 'git = "https://github.com/ambhora/nola.git"' in recipe
    assert 'version("main", branch="main")' in recipe
    assert 'version("release-next", branch="release/next")' in recipe
    assert f'version("1.2.3", tag="v1.2.3", commit="{"a" * 40}")' in recipe
    assert f'version("1.2.2", tag="1.2.2", commit="{"b" * 40}")' in recipe
    assert '"extra_widget": "extra-widget"' in recipe
    assert 'variant("extra_widget", default=False' in recipe
    assert 'depends_on("fmt@11:", when="+extra_widget")' in recipe
    assert "Threads" not in recipe
    assert "NolaDevEnv" not in recipe


def test_write_package_dry_run_does_not_modify_existing_recipe(tmp_path) -> None:
    from amstack.generate import write_package

    model = ProjectModel(
        name="nola",
        version="1.2.3",
        url="https://github.com/ambhora/nola.git",
        branches=(GitBranch("main", "main"),),
        tags=(),
        features=(),
        default_features=frozenset(),
        dependencies=(),
        dev_variants=(),
        dev_dependencies=(),
    )
    destination = tmp_path / "spack_repo/amstack/packages/nola/package.py"
    destination.parent.mkdir(parents=True)
    destination.write_text("old recipe\\n", encoding="utf-8")

    path, changed, diff = write_package(model, tmp_path, dry_run=True)

    assert path == destination
    assert changed is True
    assert destination.read_text(encoding="utf-8") == "old recipe\\n"
    assert "--- a/spack_repo/amstack/packages/nola/package.py" in diff
    assert "+++ b/spack_repo/amstack/packages/nola/package.py" in diff
    assert "-old recipe" in diff
