from __future__ import annotations

import argparse

from vending_auto_setup.config import DEFAULT_CONFIG, InstallConfig
from vending_auto_setup.installers import PhaseOneInstaller
from vending_auto_setup.os_info import print_os_info
from vending_auto_setup.runner import CommandRunner
from vending_auto_setup.system import command_exists, require_linux, require_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vending-auto-setup",
        description="Prepare Ubuntu 22.04 LTS vending machines.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")

    subcommands = parser.add_subparsers(dest="command", required=True)

    install = subcommands.add_parser("install", help="Run phase 1 installation.")
    install.add_argument("--node-major", type=int, default=DEFAULT_CONFIG.node_major)
    install.add_argument("--docker-version", default=DEFAULT_CONFIG.docker_version)
    install.add_argument("--git-version", default=DEFAULT_CONFIG.git_version)

    subcommands.add_parser("check", help="Show whether phase 1 tools are present.")
    subcommands.add_parser("about-os", help="Print OS information for bootstrap POC.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    runner = CommandRunner(dry_run=args.dry_run)

    if args.command == "check":
        for command in ("node", "npm", "docker", "git"):
            status = "found" if command_exists(runner, command) else "missing"
            print(f"{command}: {status}")
        return 0

    if args.command == "about-os":
        print_os_info()
        return 0

    if args.command == "install":
        if not args.dry_run:
            require_linux()
            require_root()

        config = InstallConfig(
            node_major=args.node_major,
            docker_version=args.docker_version,
            git_version=args.git_version,
        )
        PhaseOneInstaller(runner, config).install_all()
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
