#!/usr/bin/env python3
"""
List files in a 7-Zip archive.
"""

import argparse
from typing import List

from common import exec_7z


def _nonempty_str(s: str) -> str:
    if len(s) == 0:
        raise ValueError("Value must not be empty string")
    return s


def build_7z_command(args: argparse.Namespace) -> List[str]:
    real_args = ["l", "-bd", "-bso0", "-bsp0"]
    if not args.tabulate:
        # -ba is an undocumented switch that disables all the extra table formatting and whatnot.
        real_args.append("-ba")
    return [*real_args, "--", args.archive]


def parse_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(argument_default=None, allow_abbrev=False,
                                     description="List the files in a 7-Zip archive.")
    parser.add_argument("-t", "--tabulate", type=bool, action=argparse.BooleanOptionalAction,
                        help="Tabulate output (default: do not tabulate)", default=False, dest="tabulate")
    parser.add_argument("archive", type=_nonempty_str, help="Archive to operate on")
    return parser.parse_args(args)


def main():
    args = parse_args()
    args = build_7z_command(args)
    exec_7z(args)


if __name__ == '__main__':
    main()
