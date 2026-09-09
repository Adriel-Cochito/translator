from __future__ import annotations

import time

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QMouseEvent, QPainter, QPaintEvent, QPolygon
from PySide6.QtWidgets import QWidget

from translator.pipeline.captions import (
    is_extension,
    is_same_speech,
    is_short_continuation,
    prefer_caption,
)
from translator.pipeline.events import CaptionLine
from translator.ui.styles import speaker_color

EDGE = 12
MIN_WIDTH = 420
MIN_HEIGHT = 140


class OverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Legendas")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(960, 280)
        self._finals: list[CaptionLine] = []
        self._partials: dict[str, CaptionLine] = {}
        self._drag_origin: QPoint | None = None
        self._resize_origin: QPoint | None = None
        self._resize_geom: QRect | None = None
        self._resize_edges: tuple[bool, bool, bool, bool] | None = None
        self._opacity = 0.92
        self._phase = "stopped"
        self._mic_level = 0.0
        self._system_level = 0.0
        self._last_level_draw = 0.0

    def set_overlay_opacity(self, value: float) -> None:
        self._opacity = min(1.0, max(0.35, value))
        self.update()

    def apply_geometry(self, x: int | None, y: int | None, width: int, height: int) -> None:
        self.resize(max(MIN_WIDTH, width), max(MIN_HEIGHT, height))
        if x is not None and y is not None:
            self.move(x, y)

    def add_partial(self, line: CaptionLine) -> None:
        if any(is_same_speech(line.text, item.text) for item in self._finals[-2:]):
            return
        for source, existing in list(self._partials.items()):
            if source != line.source and is_same_speech(existing.text, line.text):
                if len(line.text) < len(existing.text):
                    return
                self._partials.pop(source, None)
        self._partials[line.source] = line
        self.update()

    def add_final(self, line: CaptionLine) -> None:
        self._partials.pop(line.source, None)
        for source, partial in list(self._partials.items()):
            if is_same_speech(partial.text, line.text):
                self._partials.pop(source, None)
        if self._finals:
            last = self._finals[-1]
            if (
                is_extension(last.text, line.text)
                or is_same_speech(last.text, line.text)
                or is_short_continuation(last.text, line.text)
            ):
                self._finals[-1] = prefer_caption(last, line)
            else:
                self._finals.append(line)
        else:
            self._finals.append(line)
        self._finals = self._finals[-4:]
        self.update()

    def rename_speaker(self, speaker_id: int, name: str) -> None:
        self._finals = [
            CaptionLine(
                item.speaker_id,
                name if item.speaker_id == speaker_id else item.speaker_name,
                item.text,
                item.is_partial,
                item.source,
            )
            for item in self._finals
        ]
        updated: dict[str, CaptionLine] = {}
        for source, item in self._partials.items():
            display = name if item.speaker_id == speaker_id else item.speaker_name
            updated[source] = CaptionLine(item.speaker_id, display, item.text, item.is_partial, item.source)
        self._partials = updated
        self.update()

    def set_phase(self, phase: str) -> None:
        self._phase = phase
        self.update()

    def set_levels(self, mic: float, system: float) -> None:
        self._mic_level = min(1.0, max(0.0, mic * 12.0))
        self._system_level = min(1.0, max(0.0, system * 12.0))
        now = time.monotonic()
        if now - self._last_level_draw < 0.25:
            return
        self._last_level_draw = now
        self.update()

    def empty_message(self) -> str:
        match self._phase:
            case "listening":
                return "Ouvindo… fale ou toque o YouTube no mesmo dispositivo"
            case "loading":
                return "Carregando modelos… microfone e sistema já estão abertos"
            case "preview":
                return "Áudio aberto. Clique em Iniciar escuta no painel"
            case _:
                return "Clique em Iniciar escuta no painel para começar"

    def clear_lines(self) -> None:
        self._finals.clear()
        self._partials.clear()
        self.update()

    def visible_lines(self) -> list[CaptionLine]:
        lines = list(self._finals)
        for partial in self._partials.values():
            if any(is_same_speech(partial.text, item.text) for item in lines):
                continue
            lines.append(partial)
        return lines

    def _hit_edges(self, pos: QPoint) -> tuple[bool, bool, bool, bool]:
        rect = self.rect()
        return (
            pos.x() <= EDGE,
            pos.x() >= rect.width() - EDGE,
            pos.y() <= EDGE,
            pos.y() >= rect.height() - EDGE,
        )

    def _update_cursor(self, pos: QPoint) -> None:
        left, right, top, bottom = self._hit_edges(pos)
        if (left and top) or (right and bottom):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif (right and top) or (left and bottom):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif left or right:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif top or bottom:
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            local = event.position().toPoint()
            edges = self._hit_edges(local)
            if any(edges):
                self._resize_edges = edges
                self._resize_origin = event.globalPosition().toPoint()
                self._resize_geom = self.geometry()
                self._drag_origin = None
            else:
                self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self._resize_edges = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._resize_edges is not None and self._resize_origin is not None and self._resize_geom is not None:
            self._apply_resize(event.globalPosition().toPoint())
        elif self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        else:
            self._update_cursor(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        self._resize_origin = None
        self._resize_geom = None
        self._resize_edges = None
        super().mouseReleaseEvent(event)

    def _apply_resize(self, global_pos: QPoint) -> None:
        if self._resize_origin is None or self._resize_geom is None or self._resize_edges is None:
            return
        left, right, top, bottom = self._resize_edges
        delta = global_pos - self._resize_origin
        geom = QRect(self._resize_geom)
        if left:
            geom.setLeft(geom.left() + delta.x())
        if right:
            geom.setRight(geom.right() + delta.x())
        if top:
            geom.setTop(geom.top() + delta.y())
        if bottom:
            geom.setBottom(geom.bottom() + delta.y())
        if geom.width() < MIN_WIDTH:
            if left:
                geom.setLeft(geom.right() - MIN_WIDTH)
            else:
                geom.setWidth(MIN_WIDTH)
        if geom.height() < MIN_HEIGHT:
            if top:
                geom.setTop(geom.bottom() - MIN_HEIGHT)
            else:
                geom.setHeight(MIN_HEIGHT)
        self.setGeometry(geom)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        background = QColor(12, 14, 18, int(230 * self._opacity))
        painter.setBrush(background)
        painter.setPen(QColor(255, 255, 255, 28))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)

        painter.setPen(QColor(154, 163, 178, 180))
        hint_font = QFont("Segoe UI", 8)
        painter.setFont(hint_font)
        painter.drawText(16, 18, "Arraste o centro para mover  ·  puxe as bordas para aumentar")

        self._paint_meters(painter)
        self._paint_resize_grip(painter)
        lines = self.visible_lines()
        if not lines:
            painter.setPen(QColor(180, 186, 196, 200))
            empty_font = QFont("Segoe UI", 13)
            painter.setFont(empty_font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_message())
            return

        body_font = QFont("Segoe UI", 16)
        painter.setFont(body_font)
        inner = QRect(18, 36, self.width() - 36, self.height() - 58)
        painter.setClipRect(inner)
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap
        laid_out: list[tuple[CaptionLine, int]] = []
        used = 0
        for line in reversed(lines):
            prefix_width = painter.fontMetrics().horizontalAdvance(f"{line.speaker_name}: ")
            text_width = max(80, inner.width() - prefix_width)
            box = QRect(0, 0, text_width, inner.height())
            height = max(28, painter.fontMetrics().boundingRect(box, int(flags), line.text).height() + 8)
            if used + height > inner.height() and laid_out:
                break
            laid_out.append((line, height))
            used += height
        y = inner.top()
        for line, height in reversed(laid_out):
            color = QColor(speaker_color(line.speaker_id))
            if line.is_partial:
                color.setAlpha(170)
            painter.setPen(color)
            prefix = f"{line.speaker_name}: "
            prefix_width = painter.fontMetrics().horizontalAdvance(prefix)
            painter.drawText(inner.left(), y + 18, prefix)
            text_color = QColor(236, 238, 241, 200 if line.is_partial else 255)
            painter.setPen(text_color)
            text_rect = QRect(inner.left() + prefix_width, y, inner.width() - prefix_width, height)
            painter.drawText(text_rect, int(flags), line.text)
            y += height

    def _paint_meters(self, painter: QPainter) -> None:
        width = 90
        height = 6
        left = self.width() - width - 22
        top = 12
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 44, 52, 200))
        painter.drawRoundedRect(left, top, width, height, 3, 3)
        painter.setBrush(QColor(125, 211, 252, 220))
        painter.drawRoundedRect(left, top, int(width * self._mic_level), height, 3, 3)
        painter.setBrush(QColor(40, 44, 52, 200))
        painter.drawRoundedRect(left, top + 10, width, height, 3, 3)
        painter.setBrush(QColor(251, 191, 36, 220))
        painter.drawRoundedRect(left, top + 10, int(width * self._system_level), height, 3, 3)

    def _paint_resize_grip(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(154, 163, 178, 160))
        x = self.width() - 16
        y = self.height() - 16
        painter.drawPolygon(QPolygon([QPoint(x, y + 10), QPoint(x + 10, y + 10), QPoint(x + 10, y)]))
