"""
theme.py — StudyBuddy AI
Single source of truth for colours, fonts, and QSS stylesheets.
Import PALETTE and STYLESHEET everywhere; do not hardcode colours in widgets.
"""

# ──────────────────────────────────────────────
# Colour palette
# ──────────────────────────────────────────────

PALETTE = {
    # Backgrounds
    "bg_deep":    "#081C15",   # evergreen
    "bg_panel":   "#1B4332",   # pine teal
    "bg_input":   "#2D6A4F",   # dark emerald

    # Borders & accents
    "border":     "#40916C",
    "accent":     "#74C69D",
    "accent_dim": "#52B788",

    # Status colors
    "danger":     "#E76F51",
    "warning":    "#F4A261",

    # Text
    "text_hi":    "#D8F3DC",
    "text_med":   "#B7E4C7",
    "text_lo":    "#95D5B2",

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
/* =====================================================
   ROOT
===================================================== */

QMainWindow, QDialog, QWidget {{
    background-color: {PALETTE['bg_deep']};
    color: {PALETTE['text_hi']};
    font-family: 'Segoe UI';
    font-size: 15px;
}}

/* =====================================================
   LABELS
===================================================== */

QLabel {{
    background: transparent;
    color: {PALETTE['text_hi']};
}}

QLabel#label_heading {{
    color: {PALETTE['text_hi']};
    font-size: 28px;
    font-weight: 700;
}}

QLabel#label_subheading {{
    color: {PALETTE['text_med']};
    font-size: 15px;
}}

QLabel#label_muted {{
    color: {PALETTE['text_med']};
    font-size: 13px;
}}

QLabel#label_stat {{
    color: {PALETTE['text_hi']};
    font-size: 34px;
    font-weight: 700;
}}

QLabel#label_error {{
    color: {PALETTE['danger']};
}}

QLabel#label_success {{
    color: {PALETTE['accent']};
}}

/* =====================================================
   CARDS
===================================================== */

QFrame#card {{
    background-color: {PALETTE['bg_panel']};
    border: 1px solid rgba(183,228,199,0.12);
    border-radius: 18px;
}}

QScrollArea {{
    border: none;
}}

/* =====================================================
   INPUTS
===================================================== */

QLineEdit,
QComboBox,
QDoubleSpinBox,
QSpinBox {{
    background-color: {PALETTE['bg_input']};
    color: {PALETTE['text_hi']};

    border: 1px solid rgba(183,228,199,0.15);
    border-radius: 12px;

    padding: 10px 14px;
}}

QLineEdit:focus,
QComboBox:focus,
QDoubleSpinBox:focus,
QSpinBox:focus {{
    border: 1px solid {PALETTE['accent']};
}}

QComboBox::drop-down {{
    border: none;
}}

QComboBox QAbstractItemView {{
    background: {PALETTE['bg_panel']};
    color: {PALETTE['text_hi']};
    border: 1px solid {PALETTE['border']};
    selection-background-color: {PALETTE['accent']};
}}

/* =====================================================
   BUTTONS
===================================================== */

QPushButton {{
    background-color: {PALETTE['accent']};

    color: {PALETTE['bg_deep']};

    border: none;
    border-radius: 12px;

    padding: 11px 22px;

    font-weight: 700;
}}

QPushButton:hover {{
    background-color: {PALETTE['accent_dim']};
}}

QPushButton:pressed {{
    padding-top: 12px;
}}

QPushButton#btn_secondary {{
    background-color: {PALETTE['bg_panel']};
    color: {PALETTE['text_hi']};

    border: 1px solid rgba(183,228,199,0.15);
}}

QPushButton#btn_secondary:hover {{
    border: 1px solid {PALETTE['accent']};
}}

QPushButton#btn_danger {{
    background-color: {PALETTE['danger']};
    color: white;
}}

QPushButton#btn_danger:hover {{
    background-color: #D65D40;
}}

QPushButton#btn_ghost {{
    background: transparent;
    border: none;

    color: {PALETTE['accent']};

    font-size: 14px;
}}

QPushButton#btn_ghost:hover {{
    color: {PALETTE['text_hi']};
}}

/* =====================================================
   TABLES
===================================================== */

QTableWidget {{
    background-color: {PALETTE['bg_panel']};

    border: 1px solid rgba(183,228,199,0.10);
    border-radius: 14px;

    gridline-color: rgba(183,228,199,0.05);
}}

QHeaderView::section {{
    background-color: {PALETTE['bg_input']};

    border: none;

    padding: 10px;

    color: {PALETTE['text_hi']};

    font-weight: 600;
}}

QTableWidget::item {{
    padding: 8px;
}}

/* =====================================================
   SCROLLBARS
===================================================== */

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {PALETTE['accent_dim']};
    border-radius: 5px;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background: {PALETTE['accent_dim']};
    border-radius: 5px;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""