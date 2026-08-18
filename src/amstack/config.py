# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Repository:
    url: str
    name: str
    branches: tuple[str, ...] = ("main",)

    @property
    def dev_environment_package(self) -> str:
        return f"{self.name}-dev-env"


def _name_from_url(url: str) -> str:
    path = urlparse(url).path if "://" in url else url
    name = Path(path.rstrip("/")).name
    if name.endswith(".git"):
        name = name[:-4]
    if not name:
        raise ConfigError(f"cannot infer repository name from URL: {url}")
    return name


def _parse_branches(value: Any) -> tuple[str, ...]:
    if value is None:
        extras: list[str] = []
    elif isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        extras = value
    else:
        raise ConfigError("repository 'branches' must be a list of non-empty strings")

    # main is always inspected; configured branches extend that default.
    return tuple(dict.fromkeys(["main", *extras]))


def _parse_repository(value: Any) -> Repository:
    if isinstance(value, str):
        return Repository(url=value, name=_name_from_url(value))

    if not isinstance(value, dict):
        raise ConfigError("each repository must be a URL string or mapping")

    url = value.get("url")
    if not isinstance(url, str) or not url:
        raise ConfigError("repository entry requires a non-empty 'url'")

    name = value.get("name", _name_from_url(url))
    if not isinstance(name, str) or not name:
        raise ConfigError("repository 'name' must be a non-empty string")

    return Repository(
        url=url,
        name=name,
        branches=_parse_branches(value.get("branches")),
    )


def load_repositories(path: Path) -> list[Repository]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError("top-level configuration must be a mapping")

    values = data.get("repositories", [])
    if not isinstance(values, list):
        raise ConfigError("'repositories' must be a list")

    repositories = [_parse_repository(value) for value in values]
    names = [repository.name for repository in repositories]
    if len(names) != len(set(names)):
        raise ConfigError("repository names must be unique")
    return repositories
