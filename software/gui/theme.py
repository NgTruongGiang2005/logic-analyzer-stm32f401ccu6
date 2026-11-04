#!/usr/bin/env python3
"""
software/gui/theme.py
Hệ thống màu sắc và stylesheet tập trung chuẩn thương mại Saleae Logic 2 / DSView.
Tất cả các màu được trích xuất trực tiếp từ đo đạc pixel thực tế (docs/UI_SPEC.md).
"""

from typing import List
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

# =============================================================================
# 1. BẢNG MÀU HỆ THỐNG THỰC ĐO (MEASURED PIXEL PALETTE)
# =============================================================================

# Màu nền chính (Nền khung sóng Viewport ~70% diện tích)
COLOR_BG_MAIN = "#1b1b1c"

# Màu nền vùng sâu (Bảng gói tin, nền sidebar lùi cấp)
COLOR_BG_DEEP = "#141415"

# Thẻ, ô điều khiển, combobox, top bar
COLOR_CARD = "#2c2c2e"

# Mục đang chọn trong sidebar, hover item
COLOR_SIDEBAR_ACTIVE = "#3a3a3e"

# Đường viền ngăn cách các vùng
COLOR_BORDER = "#3a3a3c"

# Nút Start (Xanh lá thực đo từ ảnh Saleae Logic 2)
COLOR_START_BTN = "#2e9949"
COLOR_START_BTN_HOVER = "#35ac53"
COLOR_START_BTN_BORDER = "#25833e"

# Nút Abort (Đỏ công nghiệp)
COLOR_ABORT_BTN = "#e11d48"
COLOR_ABORT_BTN_HOVER = "#f43f5e"
COLOR_ABORT_BTN_BORDER = "#be123c"

# Màu chữ
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#a0a0a2"
COLOR_TEXT_MUTED = "#71717a"

# Màu điểm nhấn (Accent)
COLOR_ACCENT = "#0284c7"
COLOR_ACCENT_HOVER = "#0369a1"

# Vạch Trigger danh định (T-Marker tại mẫu 6554)
COLOR_TRIGGER_MARKER = "#f66c7e"

# Màu cảnh báo (Warning) trong Terminal
COLOR_WARNING_AMBER = "#fbbf24"

# Màu bong bóng giải mã giao thức (In-line Decoder Bubbles)
COLOR_BUBBLE_UART = "#fde047"
COLOR_BUBBLE_I2C = "#38bdf8"
COLOR_BUBBLE_SPI = "#c084fc"

# =============================================================================
# 2. BẢNG MÀU 8 KÊNH ĐO SỐ (8-CHANNEL DIGITAL PALETTE)
# =============================================================================

SALEAE_CHANNEL_COLORS: List[str] = [
    "#d4d4d4",  # D0: Silver White (UART_TX)
    "#c39577",  # D1: Warm Copper (I2C_SCL)
    "#f66c7e",  # D2: Salmon Coral (I2C_SDA)
    "#f9b353",  # D3: Amber Orange (SPI_MOSI)
    "#e6d71a",  # D4: Lemon Yellow (SPI_MISO)
    "#67c662",  # D5: Fresh Green (SPI_SCK)
    "#4ea8de",  # D6: Sky Blue
    "#b388ff",  # D7: Lavender Violet
]

# Tương thích ngược với các module cũ
NEON_CHANNEL_COLORS = SALEAE_CHANNEL_COLORS

DEFAULT_CHANNEL_NAMES: List[str] = [
    "D0 (UART_TX)",
    "D1 (I2C_SCL)",
    "D2 (I2C_SDA)",
    "D3 (SPI_MOSI)",
    "D4 (SPI_MISO)",
    "D5 (SPI_SCK)",
    "D6",
    "D7",
]

# =============================================================================
# 3. STYLESHEET TOÀN CỤC (GLOBAL QT STYLESHEET - QSS)
# =============================================================================

DARK_THEME_QSS = f"""
QMainWindow {{
    background-color: {COLOR_BG_MAIN};
}}
QWidget {{
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 12px;
}}
QWidget#central_widget {{
    background-color: {COLOR_BG_MAIN};
}}
QLabel {{
    background-color: transparent;
    background: transparent;
}}
QFrame#top_bar {{
    background-color: {COLOR_CARD};
    border-bottom: 1px solid {COLOR_BORDER};
}}
QFrame#top_bar QLabel {{
    background-color: transparent;
    background: transparent;
}}
QFrame#top_bar QCheckBox {{
    background-color: transparent;
    background: transparent;
}}
QFrame#sidebar_container {{
    background-color: {COLOR_BG_DEEP};
    border-left: 1px solid {COLOR_BORDER};
}}
QFrame#sidebar_container QLabel {{
    background-color: transparent;
    background: transparent;
}}
QFrame#sidebar_container QCheckBox {{
    background-color: transparent;
    background: transparent;
}}
QPushButton {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 4px 10px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLOR_SIDEBAR_ACTIVE};
    border-color: #52525b;
}}
QPushButton:pressed {{
    background-color: {COLOR_ACCENT};
}}
QPushButton#btn_start {{
    background-color: {COLOR_START_BTN};
    border: 1px solid {COLOR_START_BTN_BORDER};
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
    padding: 5px 14px;
    border-radius: 4px;
}}
QPushButton#btn_start:hover {{
    background-color: {COLOR_START_BTN_HOVER};
}}
QPushButton#btn_abort {{
    background-color: {COLOR_ABORT_BTN};
    border: 1px solid {COLOR_ABORT_BTN_BORDER};
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
    padding: 5px 14px;
    border-radius: 4px;
}}
QPushButton#btn_abort:hover {{
    background-color: {COLOR_ABORT_BTN_HOVER};
}}
QPushButton#btn_abort:disabled {{
    background-color: {COLOR_CARD};
    border-color: {COLOR_BORDER};
    color: {COLOR_TEXT_MUTED};
}}
QComboBox {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 12px;
}}
QComboBox:hover {{
    border-color: #52525b;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_DEEP};
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: {COLOR_ACCENT};
    border: 1px solid {COLOR_BORDER};
}}
QCheckBox {{
    background-color: transparent;
    background: transparent;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
}}
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_BG_MAIN};
}}
QTabBar::tab {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT_SECONDARY};
    padding: 6px 12px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: bold;
    font-size: 11px;
}}
QTabBar::tab:selected {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
}}
QTableWidget {{
    background-color: {COLOR_BG_MAIN};
    alternate-background-color: {COLOR_BG_DEEP};
    color: {COLOR_TEXT_PRIMARY};
    gridline-color: {COLOR_BORDER};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    selection-background-color: {COLOR_ACCENT};
    selection-color: #ffffff;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 11px;
}}
QHeaderView::section {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT_PRIMARY};
    padding: 4px;
    font-weight: bold;
    border: 1px solid {COLOR_BORDER};
    font-size: 11px;
}}
QTextEdit {{
    background-color: {COLOR_BG_MAIN};
    color: #00f0ff;
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
}}
QStatusBar {{
    background-color: {COLOR_BG_DEEP};
    color: {COLOR_TEXT_SECONDARY};
    border-top: 1px solid {COLOR_BORDER};
    font-size: 11px;
}}
QStatusBar QLabel {{
    background-color: transparent;
    background: transparent;
    color: {COLOR_TEXT_SECONDARY};
}}
QSplitter::handle {{
    background-color: {COLOR_CARD};
}}
QSplitter::handle:hover {{
    background-color: {COLOR_ACCENT};
}}
QMenuBar {{
    background-color: {COLOR_BG_DEEP};
    color: {COLOR_TEXT_PRIMARY};
    border-bottom: 1px solid {COLOR_BORDER};
    font-size: 12px;
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 5px 10px;
}}
QMenuBar::item:selected {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
    border-radius: 2px;
}}
QMenuBar::item:pressed {{
    background-color: {COLOR_ACCENT_HOVER};
    color: #ffffff;
}}
QMenu {{
    background-color: {COLOR_BG_DEEP};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    padding: 4px 0px;
    font-size: 12px;
}}
QMenu::item {{
    background-color: transparent;
    padding: 6px 28px 6px 16px;
}}
QMenu::item:selected {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
}}
QMenu::item:disabled {{
    color: {COLOR_TEXT_MUTED};
}}
QMenu::separator {{
    height: 1px;
    background-color: {COLOR_BORDER};
    margin: 4px 8px;
}}
QToolTip {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}}
QScrollBar:vertical {{
    background-color: {COLOR_BG_MAIN};
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLOR_BORDER};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: #52525b;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {COLOR_BG_MAIN};
    height: 8px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLOR_BORDER};
    min-width: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: #52525b;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""

# =============================================================================
# 4. HÀM CẤU HÌNH PYQTGRAPH VIEWPORT CHUẨN MỰC
# =============================================================================

def setup_pyqtgraph_theme(plot_widget: pg.PlotWidget):
    """Cấu hình đồ thị pyqtgraph theo chuẩn màu nền và trục thời gian Saleae Logic 2."""
    plot_widget.setBackground(COLOR_BG_MAIN)
    plot_widget.showGrid(x=True, y=True, alpha=0.15)

    axis_bottom = plot_widget.getAxis("bottom")
    axis_bottom.setPen(pg.mkPen(color=COLOR_BORDER, width=1))
    axis_bottom.setTextPen(pg.mkPen(color=COLOR_TEXT_SECONDARY))

    axis_left = plot_widget.getAxis("left")
    axis_left.setPen(pg.mkPen(color=COLOR_BORDER, width=1))
    axis_left.setTextPen(pg.mkPen(color=COLOR_TEXT_PRIMARY))
