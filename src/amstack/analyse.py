# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import ast
import re
from pathlib import Path

from .config import Repository
from .model import BesaDependency, DevDependency, DevVariant, GitBranch, GitTag, ProjectModel


class AnalysisError(RuntimeError):
    pass


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_bool(node: ast.AST | None) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def analyse_dev_environment(package_file: Path) -> tuple[tuple[DevVariant, ...], tuple[DevDependency, ...]]:
    try:
        tree = ast.parse(package_file.read_text(encoding="utf-8"), filename=str(package_file))
    except (OSError, SyntaxError) as exc:
        raise AnalysisError(f"cannot parse development package {package_file}: {exc}") from exc

    variants: list[DevVariant] = []
    dependencies: list[DevDependency] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "variant" and node.args:
            variant_name = _literal_string(node.args[0])
            if variant_name is None:
                continue
            keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
            default = _literal_bool(keywords.get("default"))
            description = _literal_string(keywords.get("description")) or ""
            if default is not None:
                variants.append(DevVariant(variant_name, default, description))
        elif name == "depends_on" and node.args:
            spec = _literal_string(node.args[0])
            if spec is None:
                continue
            keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
            when = _literal_string(keywords.get("when"))
            dependencies.append(DevDependency(spec, when))

    return tuple(variants), tuple(dependencies)


def _cmake_call_blocks(text: str, command: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(command)}\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
    return [match.group(1) for match in pattern.finditer(text)]


def _tokens(block: str) -> list[str]:
    block = re.sub(r"#[^\n]*", "", block)
    return re.findall(r'"(?:[^"\\]|\\.)*"|[^\s]+', block)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def _values_after(tokens: list[str], keyword: str, stop_keywords: set[str]) -> list[str]:
    try:
        start = tokens.index(keyword) + 1
    except ValueError:
        return []
    result: list[str] = []
    for token in tokens[start:]:
        if token in stop_keywords:
            break
        result.append(_strip_quotes(token))
    return result


def _analyse_besa_cmake(cmake_file: Path) -> tuple[str, str, tuple[str, ...], frozenset[str], tuple[BesaDependency, ...]]:
    try:
        text = cmake_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AnalysisError(f"cannot read {cmake_file}: {exc}") from exc

    project_match = re.search(
        r"\bproject\s*\(\s*([^\s\)]+).*?\bVERSION\s+([^\s\)]+)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if project_match is None:
        raise AnalysisError(f"cannot find project(... VERSION ...) in {cmake_file}")
    project_name = project_match.group(1)
    project_version = project_match.group(2)

    features: list[str] = []
    for block in _cmake_call_blocks(text, "besa_features_add"):
        tokens = _tokens(block)
        features.extend(_values_after(tokens, "FEATURES", set()))

    defaults: list[str] = []
    for block in _cmake_call_blocks(text, "besa_features_default"):
        tokens = _tokens(block)
        defaults.extend(_values_after(tokens, "FEATURES", set()))

    dependencies: list[BesaDependency] = []
    stop = {"NAME", "VERSION", "KIND", "PROVIDER", "WHEN", "ALL_OF", "ANY_OF", "REGEX"}
    for block in _cmake_call_blocks(text, "besa_dependency_add"):
        tokens = [_strip_quotes(token) for token in _tokens(block)]
        name_values = _values_after(tokens, "NAME", stop)
        if not name_values:
            continue
        version_values = _values_after(tokens, "VERSION", stop)
        kind_values = _values_after(tokens, "KIND", stop)
        when_all_of = _values_after(tokens, "ALL_OF", stop)
        dependencies.append(
            BesaDependency(
                name=name_values[0],
                version=version_values[0] if version_values else None,
                kind=(kind_values[0] if kind_values else "NORMAL").upper(),
                when_all_of=tuple(when_all_of),
            )
        )

    return (
        project_name,
        project_version,
        tuple(dict.fromkeys(features)),
        frozenset(defaults),
        tuple(dependencies),
    )


def _find_dev_environment(repository_root: Path, package_name: str) -> Path:
    module = package_name.replace("-", "_")
    patterns = (
        f"spack/spack_repo/*/packages/{module}/package.py",
        f"spack_repo/*/packages/{module}/package.py",
    )
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(repository_root.glob(pattern))
    unique = list(dict.fromkeys(matches))
    if not unique:
        raise AnalysisError(f"cannot find BESA development package '{package_name}'")
    if len(unique) > 1:
        rendered = ", ".join(str(path.relative_to(repository_root)) for path in unique)
        raise AnalysisError(f"development package '{package_name}' is ambiguous: {rendered}")
    return unique[0]


def analyse_repository(
    repository_root: Path,
    repository: Repository,
    branches: tuple[GitBranch, ...] = (),
    tags: tuple[GitTag, ...] = (),
) -> ProjectModel:
    dev_package = _find_dev_environment(repository_root, repository.dev_environment_package)
    dev_variants, dev_dependencies = analyse_dev_environment(dev_package)
    project_name, version, features, defaults, dependencies = _analyse_besa_cmake(
        repository_root / "CMakeLists.txt"
    )

    if project_name.lower() != repository.name.lower():
        raise AnalysisError(
            f"repository '{repository.name}' contains CMake project '{project_name}'"
        )

    return ProjectModel(
        name=repository.name,
        version=version,
        url=repository.url,
        branches=branches,
        tags=tags,
        features=features,
        default_features=defaults,
        dependencies=dependencies,
        dev_variants=dev_variants,
        dev_dependencies=dev_dependencies,
    )
