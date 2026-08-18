# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import difflib
import keyword
import re
from pathlib import Path

from .model import BesaDependency, DevDependency, ProjectModel


class GenerationError(RuntimeError):
    pass


_CMAKE_BUILTINS = {"threads"}


def package_module_name(name: str) -> str:
    module = name.replace("-", "_")
    if module and module[0].isdigit():
        module = f"_{module}"
    if keyword.iskeyword(module):
        module = f"_{module}"
    if not module.isidentifier():
        raise GenerationError(f"package name cannot be represented as a Python module: {name}")
    return module


def class_name(name: str) -> str:
    words = re.split(r"[-_.]+", name)
    value = "".join(word[:1].upper() + word[1:] for word in words if word)
    if not value:
        raise GenerationError(f"cannot derive class name from package name: {name}")
    if value[0].isdigit():
        value = f"Pkg{value}"
    return value


def variant_name(feature: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", feature)
    if value and value[0].isdigit():
        value = f"feature_{value}"
    if not value or not value.isidentifier() or keyword.iskeyword(value):
        raise GenerationError(f"cannot derive Spack variant name from BESA feature: {feature}")
    return value


def _normalise_dependency_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _dev_dependency_map(dependencies: tuple[DevDependency, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for dependency in dependencies:
        result.setdefault(_normalise_dependency_name(dependency.name), dependency.name)
    return result


def _spack_dependency_name(dependency: BesaDependency, dev_dependencies: tuple[DevDependency, ...]) -> str | None:
    normalised = _normalise_dependency_name(dependency.name)
    if normalised in _CMAKE_BUILTINS:
        return None
    mapped = _dev_dependency_map(dev_dependencies).get(normalised)
    if mapped is not None:
        return mapped
    return re.sub(r"[^a-z0-9]+", "-", dependency.name.lower()).strip("-")


def _when_clause(dependency: BesaDependency, feature_variants: dict[str, str]) -> str | None:
    if not dependency.when_all_of:
        return None
    variants: list[str] = []
    for feature in dependency.when_all_of:
        variant = feature_variants.get(feature)
        if variant is None:
            return None
        variants.append(f"+{variant}")
    return " ".join(variants)


def render_package(model: ProjectModel) -> str:
    feature_variants = {feature: variant_name(feature) for feature in model.features}
    lines = [
        "# SPDX-License-Identifier: Apache-2.0",
        "",
        "from spack_repo.amstack.build_systems.ambhora_cmake import AmbhoraCMakePackage",
        "from spack.package import *",
        "",
        "",
        f"class {class_name(model.name)}(AmbhoraCMakePackage):",
        f'    """{model.name} generated from its BESA project description."""',
        "",
        f'    homepage = "{model.url.removesuffix(".git")}"',
        f'    git = "{model.url}"',
        "",
        *[
            f'    version("{branch.version}", branch="{branch.branch}")'
            for branch in model.branches
        ],
        *[
            f'    version("{tag.version}", tag="{tag.tag}", commit="{tag.commit}")'
            for tag in model.tags
        ],
        "",
        "    besa_feature_variants = {",
    ]

    for feature, variant in feature_variants.items():
        lines.append(f'        "{variant}": "{feature}",')
    lines.extend(["    }", ""])

    for feature, variant in feature_variants.items():
        default = feature in model.default_features
        lines.append(
            f'    variant("{variant}", default={default}, description="BESA feature: {feature}")'
        )
    if feature_variants:
        lines.append("")

    for dependency in model.dependencies:
        name = _spack_dependency_name(dependency, model.dev_dependencies)
        if name is None:
            continue
        spec = name
        if dependency.version:
            spec += f"@{dependency.version}:"
        when = _when_clause(dependency, feature_variants)
        arguments = [f'"{spec}"']
        if when:
            arguments.append(f'when="{when}"')
        if dependency.kind in {"BUILD", "DEV"}:
            arguments.append('type="build"')
        lines.append(f"    depends_on({', '.join(arguments)})")

    lines.append("")
    return "\n".join(lines)


def write_package(
    model: ProjectModel,
    amstack_root: Path,
    *,
    dry_run: bool = False,
) -> tuple[Path, bool, str]:
    destination = (
        amstack_root
        / "spack_repo"
        / "amstack"
        / "packages"
        / package_module_name(model.name)
        / "package.py"
    )
    contents = render_package(model)
    previous = destination.read_text(encoding="utf-8") if destination.exists() else None
    changed = previous != contents

    diff = ""
    if changed:
        relative = destination.relative_to(amstack_root).as_posix()
        diff = "".join(
            difflib.unified_diff(
                [] if previous is None else previous.splitlines(keepends=True),
                contents.splitlines(keepends=True),
                fromfile="/dev/null" if previous is None else f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )

        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(contents, encoding="utf-8")

    return destination, changed, diff
