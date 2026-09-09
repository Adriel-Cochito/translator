from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from translator.audio.devices import list_mic_devices, list_system_devices
from translator.config import AppMode, Settings
from translator.pipeline.events import CaptionLine
from translator.ui.overlay import OverlayWindow
from translator.ui.panel import ControlPanel
from translator.ui.styles import APP_QSS, make_app_icon


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    app.setWindowIcon(make_app_icon())

    panel = ControlPanel()
    overlay = OverlayWindow()
    panel.populate_devices(list_mic_devices(), list_system_devices())
    panel.apply_settings(Settings(mode=AppMode.EN_PT))
    panel.set_levels(0.08, 0.03)
    panel.set_speakers([])
    panel.show()
    overlay.show()
    overlay.resize(880, 200)
    app.processEvents()

    panel.mode_pt_en.click()
    app.processEvents()
    assert panel.collect_settings(Settings()).mode is AppMode.PT_EN

    panel.mode_sub.click()
    app.processEvents()
    assert panel.subtitle_language.isEnabled()

    overlay.add_final(CaptionLine(1, "Pessoa 1", "Hello, how are you?", False, "mic"))
    overlay.add_final(CaptionLine(2, "Pessoa 2", "Olá, tudo bem?", False, "system"))
    overlay.add_partial(CaptionLine(2, "Pessoa 2", "I am fine and...", True, "system"))
    app.processEvents()

    out = Path(__file__).resolve().parents[1] / "artifacts"
    out.mkdir(exist_ok=True)
    panel.grab().save(str(out / "panel.png"))
    overlay.grab().save(str(out / "overlay.png"))
    panel.close()
    overlay.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
