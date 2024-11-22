import re

from py7z import TIMESTAMPS


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
