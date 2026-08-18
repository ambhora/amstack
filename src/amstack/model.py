# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DevVariant:
    name: str
    default: bool
    description: str


@dataclass(frozen=True)
class DevDependency:
    spec: str
    when: str | None

    @property
    def name(self) -> str:
        value = self.spec
        for marker in ("@", "+", "~", "%", "^"):
            value = value.split(marker, 1)[0]
        return value


@dataclass(frozen=True)
class BesaDependency:
    name: str
    version: str | None
    kind: str
    when_all_of: tuple[str, ...]


@dataclass(frozen=True)
class GitBranch:
    version: str
    branch: str


@dataclass(frozen=True)
class GitTag:
    version: str
    tag: str
    commit: str


@dataclass(frozen=True)
class ProjectModel:
    name: str
    version: str
    url: str
    branches: tuple[GitBranch, ...]
    tags: tuple[GitTag, ...]
    features: tuple[str, ...]
    default_features: frozenset[str]
    dependencies: tuple[BesaDependency, ...]
    dev_variants: tuple[DevVariant, ...]
    dev_dependencies: tuple[DevDependency, ...]
