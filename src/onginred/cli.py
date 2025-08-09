from __future__ import annotations

import argparse
import json
import plistlib
from pathlib import Path

from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService


def _cmd_scaffold(args: argparse.Namespace) -> None:
    schedule = LaunchdSchedule()
    svc = LaunchdService(args.label, args.command, schedule, plist_path=args.output)
    plist = svc.to_plist_dict()
    with Path(args.output).open("wb") as f:
        plistlib.dump(plist, f)


def _cmd_inspect(args: argparse.Namespace) -> None:
    with Path(args.path).open("rb") as f:
        plist = plistlib.load(f)
    print(json.dumps(plist, indent=2))


def _apply_schedule_args(sched: LaunchdSchedule, args: argparse.Namespace) -> None:
    # Behavior
    if args.run_at_load:
        sched.behavior.run_at_load = True
    if args.keep_alive:
        sched.behavior.keep_alive = True
    if args.exit_timeout is not None:
        sched.behavior.exit_timeout = args.exit_timeout
    if args.throttle_interval is not None:
        sched.behavior.throttle_interval = args.throttle_interval

    # Time
    if args.start_interval is not None:
        sched.time.set_start_interval(args.start_interval)
    for expr in args.cron or ():
        sched.time.add_cron(expr)
    for fixed in args.at or ():
        h, m = map(int, fixed.split(":"))
        sched.time.add_fixed_time(h, m)
    for rng in args.suppress or ():
        sched.time.add_suppression_window(rng)

    # Filesystem
    for p in args.watch or ():
        sched.fs.add_watch_path(p)
    for p in args.queue or ():
        sched.fs.add_queue_directory(p)
    if args.start_on_mount:
        sched.fs.enable_start_on_mount()


def _cmd_install(args: argparse.Namespace) -> None:
    sched = LaunchdSchedule()
    _apply_schedule_args(sched, args)

    # Logging preferences
    log_dir = Path(args.log_dir).expanduser() if args.log_dir else None
    stdout_log = Path(args.stdout_log).expanduser() if args.stdout_log else None
    stderr_log = Path(args.stderr_log).expanduser() if args.stderr_log else None

    svc = LaunchdService(
        bundle_identifier=args.label,
        command=args.command if args.command else None,
        program=args.program,
        schedule=sched,
        plist_path=Path(args.plist_path).expanduser() if args.plist_path else None,
        log_dir=log_dir,
        log_name=args.log_name,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        create_dir=args.create_log_files,
    )

    svc.install()  # writes plist and calls launchctl bootstrap/load (handled internally)


def _cmd_uninstall(args: argparse.Namespace) -> None:
    # Reconstruct minimal service object to know the plist path (default or provided)
    sched = LaunchdSchedule()
    svc = LaunchdService(
        bundle_identifier=args.label,
        command=["/usr/bin/true"],  # dummy; not used for uninstall
        schedule=sched,
        plist_path=Path(args.plist_path).expanduser() if args.plist_path else None,
    )
    svc.uninstall()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="onginred")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # scaffold
    p_scaffold = sub.add_parser("scaffold", help="create a new plist from defaults")
    p_scaffold.add_argument("label", help="service label")
    p_scaffold.add_argument("command", nargs=argparse.REMAINDER, help="command to execute")
    p_scaffold.add_argument("--output", default="./launchd.plist", help="output plist path")
    p_scaffold.set_defaults(func=_cmd_scaffold)

    # inspect
    p_inspect = sub.add_parser("inspect", help="display plist as JSON")
    p_inspect.add_argument("path", help="path to plist file")
    p_inspect.set_defaults(func=_cmd_inspect)

    # shared schedule options (for install)
    def add_schedule_opts(p: argparse.ArgumentParser) -> None:
        p.add_argument("--run-at-load", action="store_true", help="set RunAtLoad=true")
        p.add_argument("--keep-alive", action="store_true", help="set KeepAlive=true")
        p.add_argument("--start-interval", type=int, help="set StartInterval (seconds)")
        p.add_argument("--cron", action="append", help='add a cron expression, e.g. "0 6 * * *"', default=[])
        p.add_argument(
            "--at", action="append", metavar="HH:MM", help="add a fixed time (24h), can repeat", default=[]
        )
        p.add_argument(
            "--suppress",
            action="append",
            metavar="HH:MM-HH:MM",
            help='add a suppression window, e.g. "23:00-06:00"',
            default=[],
        )
        p.add_argument("--watch", action="append", help="add a WatchPaths entry", default=[])
        p.add_argument("--queue", action="append", help="add a QueueDirectories entry", default=[])
        p.add_argument("--start-on-mount", action="store_true", help="enable StartOnMount")
        p.add_argument("--exit-timeout", type=int, help="ExitTimeout seconds")
        p.add_argument("--throttle-interval", type=int, help="ThrottleInterval seconds")

    # install
    p_install = sub.add_parser("install", help="write plist and load via launchctl")
    p_install.add_argument("label", help="service label")
    # Either program OR command (ProgramArguments). If both provided, Program remains but ProgramArguments are also kept.
    p_install.add_argument("--program", help="Program path to execute instead of ProgramArguments[0]")
    p_install.add_argument("command", nargs=argparse.REMAINDER, help="ProgramArguments: command and its args")
    p_install.add_argument(
        "--plist-path", help="explicit plist path (default: ~/Library/LaunchAgents/<label>.plist)"
    )
    p_install.add_argument("--log-dir", help="directory for .out/.err (overrides default /var/log)")
    p_install.add_argument("--log-name", help="basename for log files (default: label)")
    p_install.add_argument("--stdout-log", help="explicit stdout log path")
    p_install.add_argument("--stderr-log", help="explicit stderr log path")
    p_install.add_argument("--create-log-files", action="store_true", help="create log files if missing")
    add_schedule_opts(p_install)
    p_install.set_defaults(func=_cmd_install)

    # uninstall
    p_uninstall = sub.add_parser("uninstall", help="unload via launchctl and remove plist")
    p_uninstall.add_argument("label", help="service label")
    p_uninstall.add_argument("--plist-path", help="path to plist if not default")
    p_uninstall.set_defaults(func=_cmd_uninstall)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
