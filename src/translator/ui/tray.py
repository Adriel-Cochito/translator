from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from translator.ui.styles import make_app_icon


class AppTray(QSystemTrayIcon):
    def __init__(self, panel: QWidget, overlay: QWidget, on_quit) -> None:  # type: ignore[no-untyped-def]
        super().__init__(make_app_icon(), panel)
        self.setToolTip("Translator Live")
        menu = QMenu(panel)
        show_panel = QAction("Abrir painel", panel)
        show_overlay = QAction("Mostrar / esconder legendas", panel)
        quit_action = QAction("Sair", panel)
        show_panel.triggered.connect(panel.showNormal)
        show_panel.triggered.connect(panel.raise_)
        show_overlay.triggered.connect(lambda: overlay.setVisible(not overlay.isVisible()))
        quit_action.triggered.connect(on_quit)
        menu.addAction(show_panel)
        menu.addAction(show_overlay)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.activated.connect(self._activated)
        self._panel = panel

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._panel.showNormal()
            self._panel.raise_()
            self._panel.activateWindow()
