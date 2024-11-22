#!/usr/bin/env python3

import argparse
import pathlib
import sys
from typing import List
import os
import re

# <https://7-zip.opensource.jp/chm/cmdline/>
#
# Packing / unpacking: 7z, XZ, BZIP2, GZIP, TAR, ZIP and WIM
# Unpacking only: APFS, AR, ARJ, CAB, CHM, CPIO, CramFS, DMG, EXT, FAT, GPT, HFS, IHEX, ISO, LZH, LZMA, MBR,
#                 MSI, NSIS, NTFS, QCOW2, RAR, RPM, SquashFS, UDF, UEFI, VDI, VHD, VHDX, VMDK, XAR and Z.

OPERATIONS = ("add", "extract")
ARCHIVE_FORMATS = ("7z", "xz", "bzip2", "gzip", "tar", "zip", "wim")
COMPRESSION_LEVELS = ("0", "1", "3", "5", "7", "9")
COMPRESSION_METHODS = ("copy", "deflate", "deflate64", "bzip2", "lzma", "lzma2", "ppmd")
TIMESTAMPS = ("access", "creation", "modified")
CONSOLE_CHARSETS = ("utf-8", "win", "dos")
LISTFILE_CHARSETS = ("utf-8", "utf-16le", "utf-16be", "win", "dos")
OVERWRITE_MODE_LOOKUP = {
    "yes": "a",
    "skip-existing": "s",
    "rename-extracted": "u",
    "rename-existing": "t"
}


def _generic_size(s, what):
    if re.fullmatch(r"[0-9]+[bkmgt]", s, re.IGNORECASE) is not None:
        return s
    raise ValueError(f"Invalid {what} {s}")


def thread_count(s):
    s = s.lower()
    if s in ("off", "on"):
        return s
    i = int(s)
    if i < 0:
        raise ValueError("Number of threads must not be negative")
    return s


def timestamps(s):
    ts = set(s.lower().split(","))
    for t in ts:
        if t not in TIMESTAMPS:
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


def verbosity_level(c):
    return min(c, 3)


def get_7z_path():
    return os.environ.get("PY7Z_7Z_PATH", None)


def exec_7z(args):
    exec_func = os.execv
    exe_path = get_7z_path()
    if exe_path is None:
        exe_path = "7z"
        exec_func = os.execvp
    exec_func(exe_path, [exe_path, *args])


def _on_off(b):
    return "on" if b else "off"


def get_operation(args: argparse.Namespace) -> str:
    if args.operation_add:
        return "a"
    if args.operation_extract:
        return "x"
    if args.operation_list:
        return "l"
    raise ValueError("Unhandled operation")


def _make_inclusion_pattern(pattern):
    return f"!{pattern}" if pattern[0] != "@" else pattern


def _make_inclusion_arg(pattern, recurse, include_flag):
    assert include_flag in ("i", "x"), f"include flag must be i or x"
    assert re.fullmatch(r"(r[0-])?", recurse, ) is not None, "recursion option does not match regex"
    return f"-{include_flag}{recurse}{_make_inclusion_pattern(pattern)}"


def build_7z_command(args: argparse.Namespace) -> List[str]:
    real_args: List[str] = [get_operation(args)]
    if args.archive_format is not None:
        real_args.append(f"-t{args.archive_format}")
    if args.compression_method is not None:
        real_args.append(f"-mm={args.compression_method}")
    if args.compression_level is not None:
        real_args.append(f"-mx={args.compression_level}")
    if args.num_threads is not None:
        real_args.append(f"-mmt={args.num_threads}")
    if args.store_timestamps is not None:
        for t in args.store_timestamps:
            # TODO: magic constants
            if t == "access":
                real_args.append("-mta=on")
            elif t == "creation":
                real_args.append("-mtc=on")
            elif t == "modified":
                real_args.append("-mtm=on")
    if args.compress_header is not None:
        real_args.append(f"-mhc={_on_off(args.compress_header)}")
    if args.encrypt_header is not None:
        real_args.append(f"-mhe={_on_off(args.encrypt_header)}")
    if args.solid_block_size is not None:
        real_args.append(f"-ms={args.solid_block_size}")
    if args.delete_after_compression is not None and args.delete_after_compression:
        real_args.append("-sdel")
    if args.read_from_stdin is not None and args.read_from_stdin:
        real_args.append("-si")
    if args.extract_to_stdout is not None and args.extract_to_stdout:
        real_args.append("-so")
    if args.verbose is not None:
        real_args.append(f"-bb{args.verbose}")
    if args.store_symlinks_as_links is not None and args.store_symlinks_as_links:
        real_args.append("-snl")
    if args.output_directory is not None:
        real_args.append(f"-o{args.output_directory}")
    if args.recurse is not None:
        real_args.append("-r" if args.recurse else "-r-")
    if args.include is not None:
        real_args.extend(_make_inclusion_arg(p, "", "i") for p in args.include)
    if args.include_recursive is not None:
        real_args.extend(_make_inclusion_arg(p, "r", "i") for p in args.include_recursive)
    if args.exclude is not None:
        real_args.extend(_make_inclusion_arg(p, "", "x") for p in args.exclude)
    if args.exclude_recursive is not None:
        real_args.extend(_make_inclusion_arg(p, "r", "x") for p in args.exclude_recursive)
    if args.ignore_archive_name is not None and args.ignore_archive_name:
        real_args.append("-an")
    if args.enable_wildcards is not None and not args.enable_wildcards:
        real_args.append("-spd")
    if args.fail_on_bad_file is not None and args.fail_on_bad_file:
        real_args.append("-sse")
    if args.overwrite_mode is not None:
        real_args.append(f"-ao{OVERWRITE_MODE_LOOKUP[args.overwrite_mode]}")
    real_args.append(args.archive)
    if args.files is not None:
        real_args.extend(args.files)
    return real_args


def parse_args(args=None):
    parser = argparse.ArgumentParser(argument_default=None, allow_abbrev=False,
                                     description="A very bare-bones, minimal wrapper around the 7-Zip CLI.")
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument("--add", action="store_true", dest="operation_add", help="Add files to archive")
    operation_group.add_argument("--extract", action="store_true", dest="operation_extract",
                                 help="Extract files from archive")
    operation_group.add_argument("--ls", "--list", action="store_true", dest="operation_list",
                                 help="List files in archive")
    parser.add_argument("-t", "--archive-format", choices=ARCHIVE_FORMATS, required=False, dest="archive_format",
                        help="Set archive format")
    parser.add_argument("-m", "--mm", "--compression-method", choices=COMPRESSION_METHODS, required=False,
                        dest="compression_method", help="Set compression method")
    parser.add_argument("-c", "--mx", "--compression-level", choices=COMPRESSION_LEVELS, required=False,
                        dest="compression_level", help="Set compression level")
    parser.add_argument("--num-threads", "--mmt", type=thread_count, required=False, metavar="N",
                        dest="num_threads", help="Set number of threads")
    parser.add_argument("--store-timestamps", choices=TIMESTAMPS, type=timestamps, required=False,
                        dest="store_timestamps", help="Comma-separated list of timestamps to be stored")
    parser.add_argument("--compress-header", action=argparse.BooleanOptionalAction, required=False,
                        type=bool, dest="compress_header", help="Enable or disable header compression")
    parser.add_argument("--encrypt-header", action=argparse.BooleanOptionalAction, required=False,
                        type=bool, dest="encrypt_header", help="Enable or disable header encryption")
    parser.add_argument("--solid-block-size", type=solid_block_size, required=False,
                        dest="solid_block_size", metavar="SIZE",
                        help="Set solid block size (none, solid, {N}{b,k,m,g,t})")
    parser.add_argument("--delete-after-compression", action=argparse.BooleanOptionalAction, required=False,
                        type=bool, dest="delete_after_compression",
                        help="Enable or disable deleting files after compression")
    parser.add_argument("--stdin", action="store_true", required=False, default=None, dest="read_from_stdin",
                        help="Read files from stdin")
    parser.add_argument("--stdout", action="store_true", required=False, default=None, dest="extract_to_stdout",
                        help="Extract files to stdout")
    parser.add_argument("--progress", action=argparse.BooleanOptionalAction, required=False,
                        dest="show_progress", type=bool, help="Enable or disable progress indicator")
    parser.add_argument("-v", "--verbose", action="count", required=False, help="Increase verbosity")
    parser.add_argument("--store-symlinks", action=argparse.BooleanOptionalAction, required=False,
                        dest="store_symlinks_as_links", type=bool, help="Enable or disable storing symlinks as links")
    parser.add_argument("--out-dir", type=str, required=False, default=None, metavar="DIR", dest="output_directory",
                        help="Set output directory")
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
    parser.add_argument("archive", type=str, help="Archive to operate on")
    parser.add_argument("files", type=str, nargs="*", help="Files to operate on")
    # parser.print_help(sys.stdout)
    return parser.parse_args(args)


def main():
    args = parse_args()
    args = build_7z_command(args)
    exec_7z(args)


if __name__ == '__main__':
    main()
