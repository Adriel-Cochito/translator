"""Translator Live — legendas e tradução ao vivo no desktop."""

import os

from translator.cuda_paths import register_cuda_dlls

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
register_cuda_dlls()

__version__ = "1.0.0"
