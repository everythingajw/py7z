# py7z

Because the 7-Zip CLI leaves a lot to be desired.

This tool is a very, very thin wrapper around the 7-Zip CLI. It's barely anything more than simple parameter translation.
This tool makes little to no attempt to validate option compatibility - that is left up to 7-Zip.

This tool was developed and tested on Debian.

Update: this tool *used* to be only a thin wrapper around the 7-Zip CLI. I've started adding scripts that add a little bit of validation and a little bit of utility; those are `py7z-*`. The "barebones translation" tool still exists as [py7z](py7z.py).

## Installing

Prerequisites are Python and 7-Zip. The first version of this project was built with Python 3.12 and used 7-Zip 24.08.

Just put the tools somewhere on PATH. That's all.

## What's included

- [py7z](py7z.py): the "barebones translation" tool that does little more than translate parameters to 7-Zip's obtuse syntax
- [py7z-ls](py7z_ls.py): list files in an archive

## Usage

1. Call `py7z`
2. Profit

You can optionally set the environment variable `PY7Z_7Z_PATH` to use a specific path to 7-Zip. If not set, PATH is searched for `7z`.
