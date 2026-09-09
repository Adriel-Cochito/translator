"""Translator Live — legendas e tradução ao vivo no desktop."""

import os

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from translator.cuda_paths import register_cuda_dlls
from translator.ssl_certs import ensure_tls

register_cuda_dlls()
ensure_tls()

__version__ = "1.0.0"
