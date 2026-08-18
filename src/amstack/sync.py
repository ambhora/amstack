# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .analyse import AnalysisError, analyse_repository
from .config import Repository
from .generate import GenerationError, write_package
from .model import GitBranch, GitTag


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncResult:
    repository: str
    package: str
    destination: Path
    changed: bool
    diff: str


def _git_output(*args: str, cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SyncError("git executable not found") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip()
        raise SyncError(detail or f"git command failed: {' '.join(args)}") from exc
    return completed.stdout.strip()


def _run_git(*args: str, cwd: Path | None = None) -> None:
    _git_output(*args, cwd=cwd)


def _clone(repository: Repository, destination: Path) -> None:
    # A full clone is intentional: sync needs every tag and the configured branches.
    _run_git("clone", "--quiet", "--no-checkout", repository.url, str(destination))


def _spack_version_name(ref: str, *, strip_version_prefix: bool = False) -> str:
    value = ref[1:] if strip_version_prefix and re.match(r"^v\d", ref) else ref
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    if not value:
        raise SyncError(f"cannot derive a Spack version name from Git ref '{ref}'")
    return value


def _discover_branches(repository: Repository, checkout: Path) -> tuple[GitBranch, ...]:
    branches: list[GitBranch] = []
    seen_versions: dict[str, str] = {}

    for branch in repository.branches:
        try:
            _run_git("rev-parse", "--verify", f"refs/remotes/origin/{branch}", cwd=checkout)
        except SyncError as exc:
            raise SyncError(f"{repository.name}: configured branch does not exist: {branch}") from exc

        version = _spack_version_name(branch)
        previous = seen_versions.get(version)
        if previous is not None:
            raise SyncError(
                f"{repository.name}: branches '{previous}' and '{branch}' map to the same "
                f"Spack version '{version}'"
            )
        seen_versions[version] = branch
        branches.append(GitBranch(version=version, branch=branch))

    return tuple(branches)


def _discover_tags(
    repository: Repository,
    checkout: Path,
    branches: tuple[GitBranch, ...],
) -> tuple[GitTag, ...]:
    output = _git_output("tag", "--list", "--sort=-version:refname", cwd=checkout)
    tags: list[GitTag] = []
    seen_versions: dict[str, str] = {}
    branch_versions = {branch.version for branch in branches}

    for tag in output.splitlines():
        if not tag:
            continue
        version = _spack_version_name(tag, strip_version_prefix=True)
        previous = seen_versions.get(version)
        if previous is not None:
            raise SyncError(
                f"{repository.name}: tags '{previous}' and '{tag}' map to the same "
                f"Spack version '{version}'"
            )
        if version in branch_versions:
            raise SyncError(
                f"{repository.name}: tag '{tag}' conflicts with a configured branch "
                f"version '{version}'"
            )
        commit = _git_output("rev-parse", f"{tag}^{{commit}}", cwd=checkout)
        seen_versions[version] = tag
        tags.append(GitTag(version=version, tag=tag, commit=commit))

    return tuple(tags)


def _checkout_main(repository: Repository, checkout: Path) -> None:
    _run_git("checkout", "--quiet", "--detach", "refs/remotes/origin/main", cwd=checkout)


def sync_repository(
    repository: Repository,
    amstack_root: Path,
    *,
    dry_run: bool = False,
) -> SyncResult:
    try:
        with tempfile.TemporaryDirectory(prefix="amstack-") as temporary_directory:
            checkout = Path(temporary_directory) / repository.name
            _clone(repository, checkout)
            branches = _discover_branches(repository, checkout)
            tags = _discover_tags(repository, checkout, branches)
            _checkout_main(repository, checkout)
            model = analyse_repository(checkout, repository, branches, tags)
            destination, changed, diff = write_package(
                model, amstack_root, dry_run=dry_run
            )
    except (AnalysisError, GenerationError) as exc:
        raise SyncError(f"{repository.name}: {exc}") from exc

    return SyncResult(
        repository=repository.name,
        package=repository.name,
        destination=destination,
        changed=changed,
        diff=diff,
    )


def sync_all(
    repositories: list[Repository],
    amstack_root: Path,
    *,
    dry_run: bool = False,
) -> list[SyncResult]:
    return [
        sync_repository(repository, amstack_root, dry_run=dry_run)
        for repository in repositories
    ]
