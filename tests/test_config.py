from __future__ import annotations

from pathlib import Path

from translator.config import AppMode, AsrQuality, Settings, load_settings, save_settings


def test_settings_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    settings = Settings(
        mode=AppMode.PT_EN,
        subtitle_language="pt",
        asr_quality=AsrQuality.SMALL,
        mic_enabled=False,
        system_enabled=True,
        overlay_visible=False,
    )
    save_settings(settings, path)
    loaded = load_settings(path)
    assert loaded.mode is AppMode.PT_EN
    assert loaded.subtitle_language == "pt"
    assert loaded.asr_quality is AsrQuality.SMALL
    assert loaded.mic_enabled is False
    assert loaded.system_enabled is True
    assert loaded.overlay_visible is False


def test_missing_config_returns_defaults(tmp_path: Path) -> None:
    loaded = load_settings(tmp_path / "missing.json")
    assert loaded.mode is AppMode.EN_PT
    assert loaded.asr_quality is AsrQuality.TURBO
    assert loaded.mic_enabled is False
    assert loaded.system_enabled is True
    assert loaded.detect_multiple_voices is False
    assert loaded.setup_completed is False


def test_invalid_json_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not-json", encoding="utf-8")
    loaded = load_settings(path)
    assert loaded.mode is AppMode.EN_PT
