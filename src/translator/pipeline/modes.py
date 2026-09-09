from __future__ import annotations

from typing import Never

from translator.config import AppMode, Settings
from translator.translation.nllb import TranslationDirection


def asr_language(settings: Settings) -> str:
    match settings.mode:
        case AppMode.EN_PT:
            return "en"
        case AppMode.PT_EN:
            return "pt"
        case AppMode.SUBTITLE:
            return settings.subtitle_language
        case _:
            never: Never = settings.mode
            raise ValueError(f"Modo inválido: {never!r}")


def needs_translation(settings: Settings) -> bool:
    match settings.mode:
        case AppMode.EN_PT | AppMode.PT_EN:
            return True
        case AppMode.SUBTITLE:
            return False
        case _:
            never: Never = settings.mode
            raise ValueError(f"Modo inválido: {never!r}")


def translation_direction(settings: Settings) -> TranslationDirection | None:
    match settings.mode:
        case AppMode.EN_PT:
            return "en_pt"
        case AppMode.PT_EN:
            return "pt_en"
        case AppMode.SUBTITLE:
            return None
        case _:
            never: Never = settings.mode
            raise ValueError(f"Modo inválido: {never!r}")


def mode_label(mode: AppMode) -> str:
    match mode:
        case AppMode.EN_PT:
            return "Inglês → Português"
        case AppMode.PT_EN:
            return "Português → Inglês"
        case AppMode.SUBTITLE:
            return "Só legenda"
        case _:
            never: Never = mode
            raise ValueError(f"Modo inválido: {never!r}")
