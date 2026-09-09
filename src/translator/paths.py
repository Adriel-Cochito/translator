from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "TranslatorLive"


def app_data_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        root = Path(local) / APP_NAME
    else:
        root = Path.home() / f".{APP_NAME.lower()}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def models_dir() -> Path:
    path = app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return app_data_dir() / "config.json"


def whisper_dir() -> Path:
    path = models_dir() / "whisper"
    path.mkdir(parents=True, exist_ok=True)
    return path


def nllb_dir() -> Path:
    path = models_dir() / "nllb"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ecapa_dir() -> Path:
    path = models_dir() / "ecapa"
    path.mkdir(parents=True, exist_ok=True)
    return path


def silero_dir() -> Path:
    path = models_dir() / "silero"
    path.mkdir(parents=True, exist_ok=True)
    return path
