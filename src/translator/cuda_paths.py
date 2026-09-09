from __future__ import annotations

import os
import sys
from pathlib import Path


def register_cuda_dlls() -> list[str]:
    """Put pip-installed NVIDIA CUDA bins on PATH so CTranslate2 can LoadLibrary them."""
    added: list[str] = []
    roots = [
        Path(sys.prefix) / "Lib" / "site-packages" / "nvidia",
        Path(sys.prefix) / "lib" / "site-packages" / "nvidia",
    ]
    current = os.environ.get("PATH", "")
    pieces = current.split(os.pathsep) if current else []
    for root in roots:
        if not root.is_dir():
            continue
        for bin_dir in root.rglob("bin"):
            if not bin_dir.is_dir():
                continue
            if not any(bin_dir.glob("*.dll")):
                continue
            path = str(bin_dir)
            if path not in pieces:
                pieces.insert(0, path)
                added.append(path)
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(path)
                except (FileNotFoundError, OSError):
                    pass
    if added:
        os.environ["PATH"] = os.pathsep.join(pieces)
    return added
