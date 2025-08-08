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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="onginred")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scaffold = sub.add_parser("scaffold", help="create a new plist from defaults")
    p_scaffold.add_argument("label", help="service label")
    p_scaffold.add_argument("command", nargs=argparse.REMAINDER, help="command to execute")
    p_scaffold.add_argument("--output", default="./launchd.plist", help="output plist path")
    p_scaffold.set_defaults(func=_cmd_scaffold)

    p_inspect = sub.add_parser("inspect", help="display plist as JSON")
    p_inspect.add_argument("path", help="path to plist file")
    p_inspect.set_defaults(func=_cmd_inspect)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
