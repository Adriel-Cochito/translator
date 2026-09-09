from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from translator.ui.app import TranslatorApp
from translator.ui.styles import APP_QSS, make_app_icon


def main() -> int:
    os.environ["TRANSLATOR_SKIP_SETUP"] = "1"
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Translator Live")
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setStyleSheet(APP_QSS)
    qt_app.setWindowIcon(make_app_icon())
    app = TranslatorApp(qt_app)
    if not app.maybe_setup():
        return 1
    app.show_windows()
    qt_app.processEvents()

    out = Path(__file__).resolve().parents[1] / "artifacts"
    out.mkdir(exist_ok=True)
    app.panel.grab().save(str(out / "app_panel.png"))
    app.overlay.grab().save(str(out / "app_overlay.png"))

    assert app.panel.isVisible()
    assert app.overlay.isVisible()
    assert app.panel.mic_combo.count() >= 1
    assert app.panel.system_combo.count() >= 1
    assert app.panel.start_button.isEnabled()
    assert not app.pipeline.is_listening()

    QTimer.singleShot(400, qt_app.quit)
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
