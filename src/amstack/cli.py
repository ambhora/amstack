# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ConfigError, load_repositories
from .sync import SyncError, sync_all


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amstack",
        description="Generate and maintain the amstack Spack package repository.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser(
        "sync",
        help="generate package recipes from configured BESA repositories",
    )
    sync.add_argument(
        "--config",
        type=Path,
        default=Path("amstack.yaml"),
        help="repository manifest (default: amstack.yaml)",
    )
    sync.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="show generated package changes without writing them",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "sync":
        try:
            repositories = load_repositories(args.config)
            results = sync_all(
                repositories,
                args.config.resolve().parent,
                dry_run=args.dry_run,
            )
        except (ConfigError, SyncError) as exc:
            print(f"amstack: {exc}", file=sys.stderr)
            return 1

        if not results:
            print("No repositories configured.")
            return 0

        for result in results:
            if not args.dry_run:
                status = "generated" if result.changed else "unchanged"
                print(f"{result.package}: {status}")
                continue

            status = "would change" if result.changed else "unchanged"
            print(f"{result.package}: {status}")
            if result.diff:
                print(result.diff, end="" if result.diff.endswith("\n") else "\n")
        return 0

    raise AssertionError(f"unhandled command: {args.command}")
