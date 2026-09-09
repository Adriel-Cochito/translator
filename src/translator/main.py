from __future__ import annotations

import sys

from translator.ui.app import excepthook, run_app


def main() -> int:
    sys.excepthook = excepthook
    return run_app()
