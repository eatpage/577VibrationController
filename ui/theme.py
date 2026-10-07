"""配色与样式表 —— 浅色底 + 粉色主色。"""

from __future__ import annotations

# ------------------------------------------------------------ 调色板

BG = "#FFFFFF"
PANEL = "#FDF6F9"
PANEL_ALT = "#FFFFFF"
BORDER = "#F1DDE4"
BORDER_STRONG = "#E9C6D3"

TEXT = "#2F2A2C"
TEXT_MUTED = "#9A8A91"

ACCENT = "#FF5C8A"
ACCENT_HOVER = "#FF759D"
ACCENT_PRESSED = "#E8446F"
ACCENT_SOFT = "#FFE1EB"
ACCENT_SOFT_HOVER = "#FFEEF4"

LEFT_COLOR = "#FF5C8A"      # 左马达（大马达）—— 主粉
RIGHT_COLOR = "#A855F7"     # 右马达（小马达）—— 紫粉，和粉色能拉开对比

OK = "#22B573"
WARN = "#F5A623"
OFF = "#CFC6CA"

GRID = "#F7E9EF"

FONT_FAMILY = '"Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif'


def stylesheet(family: str = "") -> str:
    font_family = f'"{family}", {FONT_FAMILY}' if family else FONT_FAMILY
    return f"""
* {{
    font-family: {font_family};
    color: {TEXT};
}}

QWidget#Root {{
    background: {BG};
}}

QWidget#WaveLibrary {{
    background: #FFFFFF;
}}

QScrollArea > QWidget > QWidget {{
    background: #FFFFFF;
}}

QTabBar {{
    background: transparent;
}}

/* ---------------- 顶部栏 ---------------- */
QFrame#Header {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QLabel#AppTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {ACCENT_PRESSED};
    letter-spacing: 1px;
}}
QLabel#AppSubtitle {{
    font-size: 10px;
    color: {TEXT_MUTED};
}}
QLabel#StatusText {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}

/* ---------------- 卡片 ---------------- */
QFrame#Card {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QLabel#CardTitle {{
    font-size: 13px;
    font-weight: 700;
    color: {ACCENT_PRESSED};
}}
QLabel#Hint {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}
QLabel#Readout {{
    font-size: 12px;
    color: {TEXT};
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 8px;
}}
QLabel#Warn {{
    font-size: 11px;
    color: #B26A00;
    background: #FFF6E5;
    border: 1px solid #F7DFB4;
    border-radius: 8px;
    padding: 7px 8px;
}}

/* ---------------- 按钮 ---------------- */
QPushButton {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
}}
QPushButton:hover {{
    background: {ACCENT_SOFT_HOVER};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: {ACCENT_SOFT};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER};
    background: {PANEL};
}}

QPushButton#Primary {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #FFFFFF;
    font-weight: 700;
}}
QPushButton#Primary:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#Primary:pressed {{
    background: {ACCENT_PRESSED};
}}

/* 开关型按钮（打开状态） */
QPushButton[on="true"] {{
    background: {ACCENT_SOFT};
    border: 1px solid {ACCENT};
    color: {ACCENT_PRESSED};
    font-weight: 700;
}}
QPushButton[on="true"]:hover {{
    background: {ACCENT_SOFT_HOVER};
}}

/* 开始 / 停止 大按钮 */
QPushButton#StartButton {{
    background: {ACCENT};
    border: 2px solid {ACCENT};
    border-radius: 12px;
    color: #FFFFFF;
    font-size: 17px;
    font-weight: 700;
    padding: 14px 12px;
    letter-spacing: 3px;
}}
QPushButton#StartButton:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#StartButton:pressed {{
    background: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}
QPushButton#StartButton[running="true"] {{
    background: #FFFFFF;
    color: {ACCENT_PRESSED};
    border: 2px solid {ACCENT_PRESSED};
}}
QPushButton#StartButton[running="true"]:hover {{
    background: {ACCENT_SOFT};
}}

/* 波形按钮 */
QPushButton#WaveButton {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 9px;
    padding: 7px 4px 5px 4px;
    font-size: 12px;
    min-width: 74px;
}}
QPushButton#WaveButton:hover {{
    border-color: {ACCENT};
    background: {ACCENT_SOFT_HOVER};
}}
QPushButton#WaveButton:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #FFFFFF;
    font-weight: 700;
}}

/* ---------------- 滑杆 ---------------- */
QSlider::groove:horizontal {{
    height: 6px;
    border-radius: 3px;
    background: {ACCENT_SOFT};
}}
QSlider::sub-page:horizontal {{
    height: 6px;
    border-radius: 3px;
    background: {ACCENT};
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {ACCENT};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT};
}}
QSlider::handle:horizontal:pressed {{
    background: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}

QLabel#SliderTitle {{
    font-size: 12px;
    color: {TEXT};
}}
QLabel#SliderValue {{
    font-size: 12px;
    font-weight: 700;
    color: {ACCENT_PRESSED};
}}

/* ---------------- 下拉框 ---------------- */
QComboBox {{
    background: #FFFFFF;
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
}}
QComboBox:hover {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    border: 1px solid {BORDER_STRONG};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
    outline: none;
}}

/* ---------------- 选项卡 ---------------- */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: #FFFFFF;
    top: -1px;
}}
QTabBar::tab {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    padding: 7px 18px;
    margin-right: 4px;
    font-size: 12px;
    color: {TEXT_MUTED};
}}
QTabBar::tab:selected {{
    background: #FFFFFF;
    color: {ACCENT_PRESSED};
    font-weight: 700;
}}
QTabBar::tab:hover {{
    color: {ACCENT_PRESSED};
}}

/* ---------------- 滚动条 ---------------- */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ---------------- 聆听波束面板 ---------------- */
QFrame#BeamPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #FFF5F9, stop:0.45 #FFFFFF, stop:1 #F7F2FF);
    border: 1px solid {BORDER_STRONG};
    border-radius: 14px;
}}
QLabel#BeamTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {ACCENT_PRESSED};
    letter-spacing: 1px;
}}
QLabel#BeamStatus {{
    font-size: 11px;
    color: {TEXT_MUTED};
    background: {ACCENT_SOFT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 9px;
    padding: 3px 10px;
}}
QLabel#BeamStatus[warn="true"] {{
    color: #B26A00;
    background: #FFF6E5;
    border-color: #F7DFB4;
}}

QPushButton#ListenButton {{
    background: {PANEL_ALT};
    border: 2px solid {ACCENT};
    border-radius: 10px;
    color: {ACCENT_PRESSED};
    font-size: 14px;
    font-weight: 700;
    padding: 9px 16px;
    letter-spacing: 2px;
}}
QPushButton#ListenButton:hover {{
    background: {ACCENT_SOFT_HOVER};
}}
QPushButton#ListenButton[listening="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #FFFFFF;
}}
QPushButton#ListenButton[listening="true"]:hover {{
    background: {ACCENT_HOVER};
}}

/* ---------------- 分组标题 ---------------- */
QLabel#CategoryTitle {{
    font-size: 12px;
    font-weight: 700;
    color: {ACCENT_PRESSED};
    padding: 2px 0 0 2px;
}}

QSpinBox, QDoubleSpinBox {{
    background: #FFFFFF;
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 12px;
}}

QToolTip {{
    background: #FFFFFF;
    color: {TEXT};
    border: 1px solid {ACCENT};
    padding: 4px 8px;
    font-size: 12px;
}}
"""
