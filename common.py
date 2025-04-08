import os
from typing import List, Optional


def get_7z_path() -> Optional[str]:
    return os.environ.get("PY7Z_7Z_PATH", None)


def exec_7z(args: List[str]):
    exec_func = os.execv
    exe_path = get_7z_path()
    if exe_path is None:
        exe_path = "7z"
        exec_func = os.execvp
    exec_func(exe_path, [exe_path, *args])
