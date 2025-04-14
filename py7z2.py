#!/usr/bin/env python3
"""
General wrapper for the 7-Zip command line interface.
"""

import argparse
from common import exec_7z
import re
from typing import List
from typing import Literal
from typing import Tuple
from typing import Never
import sys

# <https://7-zip.opensource.jp/chm/cmdline/>
#
# Packing / unpacking: 7z, XZ, BZIP2, GZIP, TAR, ZIP and WIM
# Unpacking only: APFS, AR, ARJ, CAB, CHM, CPIO, CramFS, DMG, EXT, FAT, GPT, HFS, IHEX, ISO, LZH, LZMA, MBR,
#                 MSI, NSIS, NTFS, QCOW2, RAR, RPM, SquashFS, UDF, UEFI, VDI, VHD, VHDX, VMDK, XAR and Z.

OPERATIONS = ("add", "extract")
ARCHIVE_FORMATS = ("7z", "xz", "bzip2", "gzip", "tar", "zip", "wim")
COMPRESSION_LEVELS = ("0", "1", "3", "5", "7", "9")
COMPRESSION_METHODS = ("copy", "deflate", "deflate64", "bzip2", "lzma", "lzma2", "ppmd")
TIMESTAMPS_LOOKUP = {
    "access": "a",
    "creation": "c",
    "modified": "m",
}
CONSOLE_CHARSETS = ("utf-8", "win", "dos")
LISTFILE_CHARSETS = ("utf-8", "utf-16le", "utf-16be", "win", "dos")
OVERWRITE_MODE_LOOKUP = {
    "yes": "a",
    "skip-existing": "s",
    "rename-extracted": "u",
    "rename-existing": "t"
}
HASH_ALGORITHM_SHA256 = "sha256"
HASH_ALGORITHMS = ("blake2sp", "crc32", "crc64", "md5", "sha1",
                   HASH_ALGORITHM_SHA256, "sha384", "sha512", "sha3-256", "xxh64")


def die(*message, code=1):
    print(*message, file=sys.stderr)
    exit(code)


def _generic_size(s: str, what: str = "size") -> str:
    if re.fullmatch(r"[0-9]+[bkmgt]", s, re.IGNORECASE) is not None:
        return s
    raise ValueError(f"Invalid {what} {s}")


def thread_count(s: str) -> str:
    s = s.lower()
    if s in ("off", "on"):
        return s
    i = int(s)
    if i < 0:
        raise ValueError("Number of threads must not be negative")
    return s


def timestamps(s: str) -> Tuple[str, ...]:
    ts = set(s.lower().split(","))
    for t in ts:
        if t not in TIMESTAMPS_LOOKUP:
            raise ValueError(f"Invalid timestamp {t}")
    return tuple(ts)


def solid_block_size(s):
    s = s.lower()
    if s == "none":
        return "off"
    if s == "solid":
        return "on"
    return _generic_size(s, "solid block size")


def dictionary_size(s):
    return _generic_size(s, "dictionary size")


def verbosity_level(c: int) -> int:
    return min(c, 3)


def _on_off(b: bool) -> str:
    return "on" if b else "off"


OPERATION_ADD = "a"
OPERATION_LIST = "l"
OPERATION_EXTRACT = "x"
OPERATION_HASH = "h"


def get_operation(args: argparse.Namespace) -> str:
    lookup = {
        "add": OPERATION_ADD,
        "a": OPERATION_ADD,

        "list": OPERATION_LIST,
        "ls": OPERATION_LIST,
        "l": OPERATION_LIST,

        "extract": OPERATION_EXTRACT,
        "x": OPERATION_EXTRACT,

        "hash": OPERATION_HASH,
        "h": OPERATION_HASH,
    }
    if args.command_name not in lookup:
        raise ValueError("Unhandled operation")
    return lookup[args.command_name]


def compression_filter(s: str) -> str:
    # delta:{N}, bcj, bcj2, arm, armt, ia64, ppc, sparc
    if re.fullmatch(r"delta:[1-9]\d*|bcj|bcj2|arm|armt|ia64|ppc|sparc", s, re.IGNORECASE) is not None:
        return s
    raise ValueError(f"Invalid compression filter {s}")


def _make_inclusion_pattern(pattern: str) -> str:
    return f"!{pattern}" if pattern[0] != "@" else pattern


def _make_inclusion_arg(pattern: str, recurse: str, include_flag: Literal["i", "x"]) -> str:
    assert include_flag in ("i", "x"), f"include flag must be i or x"
    assert re.fullmatch(r"(r[0-])?", recurse) is not None, "recursion option does not match regex"
    return f"-{include_flag}{recurse}{_make_inclusion_pattern(pattern)}"


def build_7z_command(args: argparse.Namespace) -> List[str]:
    operation = get_operation(args)
    real_args: List[str] = [operation]

    def arg_get(attr):
        return getattr(args, attr, None)

    if operation == OPERATION_LIST:
        real_args = ["l", "-bd", "-bso0", "-bsp0"]
        if not args.tabulate:
            # -ba is an undocumented switch that disables all the extra table formatting and whatnot.
            real_args.append("-ba")
        return [*real_args, "--", args.archive]
    if operation == OPERATION_HASH:
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

    # NOTE: The == True and == False here is intentional!
    # Be extremely specific to 100% guarantee behavior. Do not coerce!
    # With == True and == False we are sure that both an option was specified *and* it has the value we want.
    # This also cleans up the pattern of "SPAM is not None and SPAM" or "SPAM is not None and not SPAM"
    # If we use just "not SPAM", then if SPAM is None (that is, it's not specified), it is passed to 7z anyway.
    # We do NOT want this behavior since the goal of this program is simple argument translation. Do NOT "create"
    # arguments that were not given.

    archive_format = arg_get("archive_format")
    if archive_format is not None:
        real_args.append(f"-t{args.archive_format}")
    if arg_get("compression_method") is not None:
        real_args.append(f"-m0={args.compression_method}")
    if arg_get("compression_level") is not None:
        real_args.append(f"-mx={args.compression_level}")
    if arg_get("num_threads") is not None:
        real_args.append(f"-mmt={args.num_threads}")
    if arg_get("store_timestamps") is not None:
        for t in args.store_timestamps:
            real_args.append(f"-mt{TIMESTAMPS_LOOKUP[t]}=on")
    if arg_get("compress_header") is not None:
        real_args.append(f"-mhc={_on_off(args.compress_header)}")
    if arg_get("encrypt_header") is not None:
        real_args.append(f"-mhe={_on_off(args.encrypt_header)}")
    if arg_get("solid_block_size") is not None:
        real_args.append(f"-ms={args.solid_block_size}")
    if arg_get("delete_after_compression") == True:
        real_args.append("-sdel")
    if arg_get("read_from_stdin") == True:
        real_args.append("-si")
    if arg_get("extract_to_stdout") == True:
        real_args.append("-so")
    if arg_get("verbose") is not None:
        real_args.append(f"-bb{args.verbose}")
    if arg_get("store_symlinks_as_links") == True:
        real_args.append("-snl")
    if arg_get('output_directory') is not None:
        real_args.append(f"-o{args.output_directory}")
    if arg_get("recurse") is not None:
        real_args.append("-r" if args.recurse else "-r-")
    if arg_get("include") is not None:
        real_args.extend(_make_inclusion_arg(p, "", "i") for p in args.include)
    if arg_get("include_recursive") is not None:
        real_args.extend(_make_inclusion_arg(p, "r", "i") for p in args.include_recursive)
    if arg_get("exclude") is not None:
        real_args.extend(_make_inclusion_arg(p, "", "x") for p in args.exclude)
    if arg_get("exclude_recursive") is not None:
        real_args.extend(_make_inclusion_arg(p, "r", "x") for p in args.exclude_recursive)
    if arg_get("ignore_archive_name") == True:
        real_args.append("-an")
    if arg_get("enable_wildcards") == False:
        real_args.append("-spd")
    if arg_get("fail_on_bad_file") == True:
        real_args.append("-sse")
    if arg_get("overwrite_mode") is not None:
        real_args.append(f"-ao{OVERWRITE_MODE_LOOKUP[args.overwrite_mode]}")
    if arg_get("show_progress") == False:
        real_args.append("-bd")
    if arg_get("assume_yes") == True:
        real_args.append("-y")

    files = arg_get("files")
    if files is not None and len(files) == 0:
        real_args.append("-si")
    archive = arg_get("archive")
    if archive == "-":
        # Writing to stdout necessitates specifying archive type
        if archive_format is None:
            die("error: must specify archive type when writing to stdout", code=1)
        real_args.append("-so")
        real_args.append("-an")
    else:
        real_args.append(archive)
    if files is not None and len(files) > 0:
        real_args.extend(args.files)
    return real_args


def parse_args(args=None):
    parser = argparse.ArgumentParser(argument_default=None, allow_abbrev=False,
                                     description="A very bare-bones, minimal wrapper around the 7-Zip CLI.")

    subparsers = parser.add_subparsers(dest="command_name", required=True)

    # Creating a new archive and adding files to an existing archive
    add_parser = subparsers.add_parser("add", aliases=["a"], help="Add files to an archive")
    add_parser.add_argument("-t", "--archive-format", choices=ARCHIVE_FORMATS, required=False, dest="archive_format",
                            help="Set archive format")
    add_parser.add_argument("-m", "--mm", "--compression-method", choices=COMPRESSION_METHODS, required=False,
                            dest="compression_method", help="Set compression method")
    add_parser.add_argument("-c", "--mx", "--compression-level", choices=COMPRESSION_LEVELS, required=False,
                            dest="compression_level", help="Set compression level")
    add_parser.add_argument("--num-threads", "--mmt", type=thread_count, required=False, metavar="N",
                            dest="num_threads",
                            help="Set number of threads ('on' to automatically determine number of threads, 'off' to disable multithreading)")
    add_parser.add_argument("--filter", "--mf", type=compression_filter, dest="compression_filter",
                            help="Use the specified compression filter for all files (one of delta:{N}, bcj, bcj2, arm, armt, ia64, ppc, sparc")
    add_parser.add_argument("--store-timestamps", choices=TIMESTAMPS_LOOKUP.keys(), type=timestamps, required=False,
                            dest="store_timestamps", help="Comma-separated list of timestamps to be stored")
    add_parser.add_argument("--mhc", "--compress-header", action=argparse.BooleanOptionalAction, required=False,
                            type=bool, dest="compress_header", help="Enable or disable header compression")
    add_parser.add_argument("--mhe", "--encrypt-header", action=argparse.BooleanOptionalAction, required=False,
                            type=bool, dest="encrypt_header", help="Enable or disable header encryption")
    add_parser.add_argument("--solid-block-size", type=solid_block_size, required=False,
                            dest="solid_block_size", metavar="SIZE",
                            help="Set solid block size (none, solid, {N}{b,k,m,g,t})")
    add_parser.add_argument("--delete-after-compression", action=argparse.BooleanOptionalAction, required=False,
                            type=bool, dest="delete_after_compression",
                            help="Enable or disable deleting files after compression")
    add_parser.add_argument("--store-symlinks", action=argparse.BooleanOptionalAction, required=False,
                            dest="store_symlinks_as_links", type=bool,
                            help="Enable or disable storing symlinks as links")
    add_parser.add_argument("archive", type=str, help="Archive to operate on")
    add_parser.add_argument("files", type=str, nargs="*",
                            help="Files to operate on. If none provided, read from stdin.")

    # Listing the contents of an archive
    list_parser = subparsers.add_parser("list", aliases=["l", "ls"], help="List files in archive")
    list_parser.add_argument("-t", "--tabulate", type=bool, action=argparse.BooleanOptionalAction,
                             help="Tabulate output (default: do not tabulate)", default=False, dest="tabulate")
    list_parser.add_argument("archive", type=str, help="Archive to operate on")

    # Hashing an archive
    hash_parser = subparsers.add_parser("hash", aliases=["h"], help="Hash files or archive contents")
    hash_parser.add_argument("-a", "--algorithm", required=False, choices=HASH_ALGORITHMS,
                             default=HASH_ALGORITHM_SHA256, dest="hash_algorithm",
                             help=f"Set the hash algorithm to use (default: {HASH_ALGORITHM_SHA256})"),
    hash_parser.add_argument("-v", "--verbose", required=False, action=argparse.BooleanOptionalAction,
                             default=False, dest="verbose",
                             help="Increase verbosity and show results as a table (default: be quiet)")
    hash_parser.add_argument("-p", "--progress", required=False, action=argparse.BooleanOptionalAction,
                             default=False, dest="show_progress",
                             help="Show progress as each file is hashed (default: do not show progress)")
    hash_parser.add_argument("-c", "--archive-contents", required=False, default=False, action="store_true",
                             dest="hash_archive_contents", help="Hash archive contents, not the archive itself")
    hash_parser.add_argument("files", nargs='*',
                             help="Files to hash. When no files are specified, read from stdin. When combined with --archive-contents, one file other than stdin must be specified (due to 7-Zip limitations).")

    # Options for extracting files
    extract_parser = subparsers.add_parser("extract", aliases=["ex", "x"], help="Extract files from archive")
    extract_parser.add_argument("--stdout", action="store_true", required=False, default=None, dest="extract_to_stdout",
                                help="Extract files to stdout")
    extract_parser.add_argument("-o", "--out-dir", type=str, required=False, default=None, metavar="DIR",
                                dest="output_directory", help="Set output directory")
    extract_parser.add_argument("-y", "--yes", action="store_true", required=False, default=None, dest="assume_yes",
                                help="Assume yes on all operations (equivalent to -y)")
    extract_parser.add_argument("archive", type=str, help="Archive to operate on")

    # Other options
    parser.add_argument("--stdin", action="store_true", required=False, default=None, dest="read_from_stdin",
                        help="Read files from stdin")
    parser.add_argument("--stdout", action="store_true", required=False, default=None, dest="extract_to_stdout",
                        help="Extract files to stdout")
    parser.add_argument("--progress", action=argparse.BooleanOptionalAction, required=False,
                        dest="show_progress", type=bool, help="Enable or disable progress indicator")
    parser.add_argument("-v", "--verbose", action="count", required=False, help="Increase verbosity")
    parser.add_argument("-r", "--recurse", action=argparse.BooleanOptionalAction, required=False, dest="recurse",
                        help="Enable or disable recursion")
    parser.add_argument("-i", "--include", action="append", required=False, metavar="PAT", dest="include",
                        help="Include files from pattern or wildcard (equivalent to -i@/i!)")
    parser.add_argument("-I", "--include-recursive", action="append", required=False, metavar="PAT",
                        dest="include_recursive",
                        help="Recursively include files from pattern or wildcard (equivalent to -ir@/-ir!)")
    parser.add_argument("-x", "--exclude", action="append", required=False, metavar="PAT", dest="exclude",
                        help="Exclude files from pattern or wildcard (equivalent to -x@/x!)")
    parser.add_argument("-X", "--exclude-recursive", action="append", required=False, metavar="PAT",
                        dest="exclude_recursive",
                        help="Exclude files from pattern or wildcard (equivalent to -xr@/ir!)")
    parser.add_argument("--an", "--ignore-archive-name", action="store_true", required=False,
                        dest="ignore_archive_name", help="Disable archive name parsing (equivalent to -an)")
    parser.add_argument("--console-charset", choices=CONSOLE_CHARSETS, required=False, dest="console_charset",
                        help="Set character set for console output (equivalent to -scc)")
    parser.add_argument("--listfile-charset", choices=LISTFILE_CHARSETS, required=False, dest="listfile_charset",
                        help="Set character set for listfiles (equivalent to -scs)")
    parser.add_argument("--wildcards", action=argparse.BooleanOptionalAction, required=False, dest="enable_wildcards",
                        help="Enable or disable wildcard matching")
    parser.add_argument("--fail-on-bad-file", action="store_true", required=False, dest="fail_on_bad_file",
                        help="Stop if an input file cannot be read (equivalent to -sse)")
    parser.add_argument("--overwrite", choices=(OVERWRITE_MODE_LOOKUP.keys()),
                        required=False, default=None, dest="overwrite_mode",
                        help="Specify how files should be overwritten (equivalent to -ao)")
    parser.add_argument("-y", "--yes", action="store_true", required=False, default=None, dest="assume_yes",
                        help="Assume yes on all operations (equivalent to -y)")
    # parser.add_argument("archive", type=str, help="Archive to operate on")

    parser.print_help()
    add_parser.print_help()
    list_parser.print_help()
    hash_parser.print_help()
    extract_parser.print_help()
    sys.stdout.flush()
    sys.stderr.flush()

    return parser.parse_args(args)


def main():
    args = parse_args("add -t 7z --filter Ia64 -".split())
    # print(args)
    args = build_7z_command(args)
    print(args)
    # exec_7z(args)


if __name__ == '__main__':
    main()
