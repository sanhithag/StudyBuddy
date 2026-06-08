"""
widgets.py — StudyBuddy AI
Small reusable PyQt6 widgets used across multiple pages.
"""

from PyQt6.QtWidgets import QLabel, QFrame, QHBoxLayout, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush

from theme import PALETTE


# ──────────────────────────────────────────────
# Section separator
# ──────────────────────────────────────────────

class HDivider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet("color: rgba(183,228,199,0.12); margin: 8px 0;")

class StatCard(QFrame):
    def __init__(self, title, value='—', unit='', parent=None):
        super().__init__(parent)
        self.setObjectName('card')
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,18,20,18)

        self._val_label = QLabel(value)
        self._val_label.setObjectName('label_stat')
        self._val_label.setFont(QFont('Segoe UI', 28, QFont.Weight.Bold))

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel(title))
        if unit:
            title_row.addWidget(QLabel(unit))
        title_row.addStretch()

        layout.addWidget(self._val_label)
        layout.addLayout(title_row)

    def set_value(self, v):
        self._val_label.setText(v)

class AvatarCircle(QWidget):
    def __init__(self, initials='?', color='#74C69D', size=64, parent=None):
        super().__init__(parent)
        self._initials = initials[:2].upper()
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size, size)

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def set_initials(self, initials):
        self._initials = initials[:2].upper()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(2, 2, self._size - 4, self._size - 4)
        p.setPen(QColor(PALETTE['bg_deep']))
        p.setFont(QFont('Segoe UI', self._size // 3, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initials)
        p.end()


# ──────────────────────────────────────────────
# Color picker row (circle toggle buttons)
# ──────────────────────────────────────────────

class ColorPickerRow(QWidget):
    """Row of clickable coloured circles to pick a theme colour."""

    from PyQt6.QtCore import pyqtSignal

    color_selected = pyqtSignal(str)

    def __init__(self, colors: list[str], current: str = "", parent=None):
        super().__init__(parent)
        self._current = current
        self._btns: dict[str, QLabel] = {}
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        for c in colors:
            lbl = _ColorDot(c, c == current)
            lbl.clicked.connect(lambda col=c: self._pick(col))
            self._btns[c] = lbl
            row.addWidget(lbl)
        row.addStretch()

    def _pick(self, color: str) -> None:
        for c, btn in self._btns.items():
            btn.set_selected(c == color)
        self._current = color
        self.color_selected.emit(color)

    def current_color(self) -> str:
        return self._current


class _ColorDot(QWidget):
    from PyQt6.QtCore import pyqtSignal
    clicked = pyqtSignal()

    def __init__(self, color: str, selected: bool = False, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._selected = selected
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_selected(self, v: bool) -> None:
        self._selected = v
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._selected:
            p.setPen(QColor("#FFFFFF"))
            p.drawEllipse(1, 1, 26, 26)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(4, 4, 20, 20)
        p.end()


# ──────────────────────────────────────────────
# Inline message banner
# ──────────────────────────────────────────────

class MessageBanner(QLabel):
    """One-line success / error banner. Hidden by default."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def show_error(self, msg: str) -> None:
        self.setObjectName("label_error")
        self.setStyleSheet(
            f"color: {PALETTE['danger']}; background: rgba(239,68,68,0.12);"
            "border-radius: 6px; padding: 6px 12px;"
        )
        self.setText(msg)
        self.show()

    def show_success(self, msg: str) -> None:
        self.setObjectName("label_success")
        self.setStyleSheet(
            f"color: {PALETTE['accent']}; background: rgba(16,185,129,0.12);"
            "border-radius: 6px; padding: 6px 12px;"
        )
        self.setText(msg)
        self.show()

    def clear(self) -> None:
        self.hide()
        self.setText("")