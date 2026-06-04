from __future__ import annotations

import argparse

from vending_auto_setup.config import DEFAULT_CONFIG, InstallConfig
from vending_auto_setup.display import ROTATION_MATRICES, DisplayConfigurator
from vending_auto_setup.installers import PhaseOneInstaller
from vending_auto_setup.os_info import print_os_info
from vending_auto_setup.runner import CommandRunner
from vending_auto_setup.status import print_status
from vending_auto_setup.system import require_linux, require_root


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

    display = subcommands.add_parser("display", help="Inspect and configure X11 display/touchscreen settings.")
    display_subcommands = display.add_subparsers(dest="display_command", required=True)

    display_status = display_subcommands.add_parser("status", help="Show xrandr and xinput status.")
    add_x_session_arguments(display_status)

    display_apply = display_subcommands.add_parser("apply", help="Apply display rotation and touchscreen mapping now.")
    add_x_session_arguments(display_apply)
    display_apply.add_argument("--output", required=True, help="xrandr output name, for example HDMI-1 or Virtual1.")
    display_apply.add_argument("--touch", required=True, help="xinput touchscreen name or id.")
    display_apply.add_argument("--rotate", choices=sorted(ROTATION_MATRICES), required=True)

    display_persist = display_subcommands.add_parser(
        "persist-xorg",
        help="Persist touchscreen coordinate mapping with an Xorg InputClass config.",
    )
    display_persist.add_argument("--touch", required=True, help="xinput touchscreen product name.")
    display_persist.add_argument("--rotate", choices=sorted(ROTATION_MATRICES), required=True)

    display_persist_session = display_subcommands.add_parser(
        "persist-session",
        help="Persist display rotation and touchscreen mapping in the user's X session profile.",
    )
    add_x_session_arguments(display_persist_session)
    display_persist_session.add_argument(
        "--output",
        required=True,
        help="xrandr output name, for example HDMI-1 or Virtual1.",
    )
    display_persist_session.add_argument("--touch", required=True, help="xinput touchscreen name or id.")
    display_persist_session.add_argument("--rotate", choices=sorted(ROTATION_MATRICES), required=True)
    display_persist_session.add_argument("--delay-seconds", type=int, default=5)
    display_persist_session.add_argument("--retries", type=int, default=30)
    return parser


def add_x_session_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--display",
        "--x-display",
        dest="x_display",
        help="X display value, for example :0. Defaults to current DISPLAY.",
    )
    parser.add_argument("--xauthority", help="Optional XAUTHORITY file for controlling another user's X session.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    runner = CommandRunner(dry_run=args.dry_run)

    if args.command == "check":
        print_status()
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

    if args.command == "display":
        configurator = DisplayConfigurator(runner)

        if args.display_command == "status":
            configurator.print_status(x_display=args.x_display, xauthority=args.xauthority)
            return 0

        if args.display_command == "apply":
            configurator.apply_runtime(
                output=args.output,
                touch=args.touch,
                rotate=args.rotate,
                x_display=args.x_display,
                xauthority=args.xauthority,
            )
            return 0

        if args.display_command == "persist-xorg":
            if not args.dry_run:
                require_linux()
                require_root()
            configurator.persist_xorg(touch=args.touch, rotate=args.rotate)
            return 0

        if args.display_command == "persist-session":
            configurator.persist_session(
                output=args.output,
                touch=args.touch,
                rotate=args.rotate,
                x_display=args.x_display,
                delay_seconds=args.delay_seconds,
                retries=args.retries,
            )
            return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
