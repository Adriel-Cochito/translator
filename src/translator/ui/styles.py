from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtCore import Qt


SPEAKER_COLORS = [
    "#7dd3fc",
    "#fbbf24",
    "#86efac",
    "#fb7185",
    "#c4b5fd",
    "#67e8f9",
    "#fdba74",
    "#f9a8d4",
]

APP_QSS = """
QWidget {
    background-color: #16181d;
    color: #e8eaed;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #16181d;
}
QGroupBox {
    border: 1px solid #2c313a;
    border-radius: 10px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #9aa3b2;
}
QPushButton {
    background-color: #2a303a;
    border: 1px solid #3a4150;
    border-radius: 8px;
    padding: 8px 14px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #353c48;
}
QPushButton:pressed {
    background-color: #1f242c;
}
QPushButton#primary {
    background-color: #2563eb;
    border: 1px solid #1d4ed8;
    font-weight: 700;
}
QPushButton#primary:hover {
    background-color: #1d4ed8;
}
QPushButton#danger {
    background-color: #7f1d1d;
    border: 1px solid #991b1b;
}
QComboBox, QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #1e2229;
    border: 1px solid #343b48;
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: #2563eb;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QCheckBox, QRadioButton {
    spacing: 8px;
}
QProgressBar {
    background-color: #1e2229;
    border: 1px solid #343b48;
    border-radius: 6px;
    text-align: center;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #38bdf8;
    border-radius: 5px;
}
QLabel#status {
    color: #9aa3b2;
}
QLabel#title {
    font-size: 18px;
    font-weight: 700;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #2a303a;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #7dd3fc;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QScrollArea {
    border: none;
    background-color: #16181d;
}
"""


def speaker_color(speaker_id: int) -> str:
    if speaker_id <= 0:
        return "#9aa3b2"
    return SPEAKER_COLORS[(speaker_id - 1) % len(SPEAKER_COLORS)]


def make_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2563eb"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", 22, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    painter.end()
    return QIcon(pixmap)
