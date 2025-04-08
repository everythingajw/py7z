#!/usr/bin/env python3

import argparse
import common
from typing import List
import sys

HASH_ALGORITHM_SHA256 = "sha256"
HASH_ALGORITHMS = ("blake2sp", "crc32", "crc64", "md5", "sha1",
                   HASH_ALGORITHM_SHA256, "sha384", "sha512", "sha3-256", "xxh64")


def build_7z_command(args) -> List[str]:
    real_args = ["h"]
    if args.hash_archive_contents:
        real_args = ["t", "-slt"]
        if len(args.files) != 1:
            print("Exactly 1 file must be specified when hashing archive contents", file=sys.stderr)
            exit(1)

    if not args.verbose:
        real_args.append("-ba")
    if not args.show_progress:
        real_args.append("-bd")
        real_args.append("-bsp0")

    real_args.append(f"-scrc{args.hash_algorithm}")
    if len(args.files) == 0:
        real_args.append("-si")
    else:
        real_args.append("--")
        real_args.extend(args.files)
    return real_args


def parse_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(argument_default=None, allow_abbrev=False,
                                     description="Hash file(s) with 7-Zip.")
    parser.add_argument("-a", "--algorithm", required=False, choices=HASH_ALGORITHMS,
                        default=HASH_ALGORITHM_SHA256, dest="hash_algorithm",
                        help=f"Set the hash algorithm to use (default: {HASH_ALGORITHM_SHA256})"),
    parser.add_argument("-v", "--verbose", required=False, action=argparse.BooleanOptionalAction,
                        default=False, dest="verbose",
                        help="Increase verbosity and show results as a table (default: be quiet)")
    parser.add_argument("-p", "--progress", required=False, action=argparse.BooleanOptionalAction,
                        default=False, dest="show_progress",
                        help="Show progress as each file is hashed (default: do not show progress)")
    parser.add_argument("-c", "--archive-contents", required=False, default=False, action="store_true",
                        dest="hash_archive_contents", help="Hash archive contents, not the archive itself")
    parser.add_argument("files", nargs='*',
                        help="Files to hash. When no files are specified, read from stdin. When combined with --archive-contents, one file other than stdin must be specified (due to 7-Zip limitations).")
    return parser.parse_args(args)


def main():
    args = parse_args()
    args = build_7z_command(args)
    common.exec_7z(args)


if __name__ == '__main__':
    main()
