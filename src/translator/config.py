from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from translator.paths import config_path


class AppMode(StrEnum):
    EN_PT = "en_pt"
    PT_EN = "pt_en"
    SUBTITLE = "subtitle"


class AsrQuality(StrEnum):
    TURBO = "large-v3-turbo"
    MEDIUM = "medium"
    SMALL = "small"


SubtitleLanguage = Literal["en", "pt"]


@dataclass
class Settings:
    mode: AppMode = AppMode.EN_PT
    subtitle_language: SubtitleLanguage = "en"
    asr_quality: AsrQuality = AsrQuality.TURBO
    mic_enabled: bool = False
    system_enabled: bool = True
    mic_device: str | None = None
    system_device: str | None = None
    detect_multiple_voices: bool = False
    overlay_visible: bool = True
    overlay_opacity: float = 0.92
    overlay_x: int | None = None
    overlay_y: int | None = None
    overlay_width: int = 960
    overlay_height: int = 280
    setup_completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = str(self.mode)
        data["asr_quality"] = str(self.asr_quality)
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Settings:
        known = {field: raw[field] for field in cls.__dataclass_fields__ if field in raw}
        if "mode" in known:
            known["mode"] = AppMode(known["mode"])
        if "asr_quality" in known:
            try:
                known["asr_quality"] = AsrQuality(known["asr_quality"])
            except ValueError:
                known["asr_quality"] = AsrQuality.TURBO
        language = known.get("subtitle_language", "en")
        if language not in ("en", "pt"):
            known["subtitle_language"] = "en"
        return cls(**known)


def load_settings(path: Path | None = None) -> Settings:
    target = path or config_path()
    if not target.exists():
        return Settings()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()
    return Settings.from_dict(raw)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
