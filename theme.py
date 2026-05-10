"""
theme.py — StudyBuddy AI
Single source of truth for colours, fonts, and QSS stylesheets.
Import PALETTE and STYLESHEET everywhere; do not hardcode colours in widgets.
"""

# ──────────────────────────────────────────────
# Colour palette
# ──────────────────────────────────────────────

PALETTE = {
    "bg_deep":    "#080B14",   # outermost background
    "bg_panel":   "#0F1221",   # card / panel background
    "bg_input":   "#161929",   # text-input background
    "border":     "#1E2540",   # subtle borders
    "accent":     "#10B981",   # primary green accent
    "accent_dim": "#059669",   # darker accent for hover
    "danger":     "#EF4444",
    "warning":    "#F59E0B",
    "text_hi":    "#E8EDF5",   # high-emphasis text
    "text_med":   "#8B95A8",   # medium-emphasis / labels
    "text_lo":    "#3D4663",   # low-emphasis / disabled
    "white":      "#FFFFFF",
}

# Avatar colour presets shown in profile picker
AVATAR_COLORS = [
    "#10B981", "#3B82F6", "#8B5CF6",
    "#F59E0B", "#EC4899", "#EF4444",
    "#06B6D4", "#84CC16",
]

# ──────────────────────────────────────────────
# Global QSS stylesheet
# ──────────────────────────────────────────────

STYLESHEET = f"""
/* ── Root ─────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {PALETTE['bg_deep']};
    color: {PALETTE['text_hi']};
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 13px;
}}

/* ── Labels ───────────────────────────────── */
QLabel {{
    color: {PALETTE['text_hi']};
    background: transparent;
}}
QLabel#label_muted {{
    color: {PALETTE['text_med']};
    font-size: 11px;
}}
QLabel#label_heading {{
    color: {PALETTE['accent']};
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#label_subheading {{
    color: {PALETTE['text_med']};
    font-size: 13px;
}}
QLabel#label_stat {{
    color: {PALETTE['white']};
    font-size: 28px;
    font-weight: 700;
}}
QLabel#label_error {{
    color: {PALETTE['danger']};
    font-size: 12px;
}}
QLabel#label_success {{
    color: {PALETTE['accent']};
    font-size: 12px;
}}

/* ── Input fields ─────────────────────────── */
QLineEdit, QComboBox, QTextEdit {{
    background-color: {PALETTE['bg_input']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 10px 14px;
    color: {PALETTE['text_hi']};
    selection-background-color: {PALETTE['accent']};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {PALETTE['accent']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {PALETTE['bg_panel']};
    color: {PALETTE['text_hi']};
    selection-background-color: {PALETTE['accent']};
    border: 1px solid {PALETTE['border']};
}}

/* ── Buttons ──────────────────────────────── */
QPushButton {{
    background-color: {PALETTE['accent']};
    color: #000000;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 11px 22px;
    letter-spacing: 0.5px;
}}
QPushButton:hover {{
    background-color: {PALETTE['accent_dim']};
}}
QPushButton:pressed {{
    background-color: #047857;
}}
QPushButton#btn_secondary {{
    background-color: {PALETTE['bg_panel']};
    color: {PALETTE['text_hi']};
    border: 1px solid {PALETTE['border']};
}}
QPushButton#btn_secondary:hover {{
    border-color: {PALETTE['accent']};
    color: {PALETTE['accent']};
}}
QPushButton#btn_danger {{
    background-color: {PALETTE['danger']};
    color: white;
}}
QPushButton#btn_danger:hover {{
    background-color: #DC2626;
}}
QPushButton#btn_ghost {{
    background-color: transparent;
    color: {PALETTE['accent']};
    border: none;
    padding: 4px 0px;
    font-size: 12px;
    text-align: left;
}}
QPushButton#btn_ghost:hover {{
    color: {PALETTE['text_hi']};
}}

/* ── Cards / Frames ───────────────────────── */
QFrame#card {{
    background-color: {PALETTE['bg_panel']};
    border: 1px solid {PALETTE['border']};
    border-radius: 12px;
}}

/* ── Table ────────────────────────────────── */
QTableWidget {{
    background-color: {PALETTE['bg_panel']};
    color: {PALETTE['text_hi']};
    gridline-color: {PALETTE['border']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
}}
QTableWidget::item:selected {{
    background-color: rgba(16,185,129,0.2);
    color: {PALETTE['white']};
}}
QHeaderView::section {{
    background-color: {PALETTE['bg_deep']};
    color: {PALETTE['text_med']};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {PALETTE['border']};
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
}}

/* ── Scrollbars ───────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {PALETTE['border']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Spinbox ──────────────────────────────── */
QDoubleSpinBox, QSpinBox {{
    background-color: {PALETTE['bg_input']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {PALETTE['text_hi']};
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {PALETTE['accent']};
}}
"""
