#!/usr/bin/env python3
"""
software/gui/main_window.py
Giao diện người dùng Desktop chuẩn thương mại 3 Vùng Tách Biệt (Saleae Logic 2 / DSView):
- Vùng 1: Thanh điều khiển ngang đỉnh giao diện (Top Control Bar - Cao đúng 45px - Cố định)
- Vùng 2: Khung vẽ sóng trung tâm (Waveform Viewport - 72% bề ngang) với 8 kênh neon, T-Marker t=0, Cursors A/B, HUD
- Vùng 3: Cột điều khiển & giải mã bên phải (Right Sidebar - 28% bề ngang, QSplitter)
    + Tab 1: Protocol Decoder & Packet Table (UART, I2C, SPI, Click-to-Jump)
    + Tab 2: Export & Channel Tools (PNG/SVG, CSV, VCD, Quản lý kênh)
- Vùng 4: Thanh trạng thái đáy (Status Bar - Cao 25px)
"""

import os
import sys
import time
import numpy as np
from typing import Optional, Dict, Any, List

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from software.gui.logic_client import LogicAnalyzerClient
from software.gui.waveform_widget import WaveformWidget, NEON_CHANNEL_COLORS
from software.decoders.uart_decoder import UARTDecoder
from software.decoders.i2c_decoder import I2CDecoder
from software.decoders.spi_decoder import SPIDecoder
from software.utils.exporter import export_image, export_csv, export_vcd


DARK_THEME_CSS = """
QMainWindow {
    background-color: #18181b;
}
QWidget {
    color: #e4e4e7;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 12px;
}
QWidget#central_widget {
    background-color: #18181b;
}
QLabel {
    background-color: transparent;
    background: transparent;
}
QFrame#top_bar {
    background-color: #27272a;
    border-bottom: 1px solid #3f3f46;
}
QFrame#top_bar QLabel {
    background-color: transparent;
    background: transparent;
}
QFrame#top_bar QCheckBox {
    background-color: transparent;
    background: transparent;
}
QFrame#sidebar_container {
    background-color: #202023;
    border-left: 1px solid #3f3f46;
}
QFrame#sidebar_container QLabel {
    background-color: transparent;
    background: transparent;
}
QFrame#sidebar_container QCheckBox {
    background-color: transparent;
    background: transparent;
}
QPushButton {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 4px 10px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #3f3f46;
    border-color: #71717a;
}
QPushButton:pressed {
    background-color: #0284c7;
}
QPushButton#btn_start {
    background-color: #10b981;
    border: 1px solid #059669;
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
    padding: 5px 14px;
}
QPushButton#btn_start:hover {
    background-color: #059669;
}
QPushButton#btn_abort {
    background-color: #ef4444;
    border: 1px solid #dc2626;
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
    padding: 5px 14px;
}
QPushButton#btn_abort:hover {
    background-color: #dc2626;
}
QPushButton#btn_abort:disabled {
    background-color: #27272a;
    border-color: #3f3f46;
    color: #71717a;
}
QComboBox {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 12px;
}
QComboBox:hover {
    border-color: #00f0ff;
}
QComboBox QAbstractItemView {
    background-color: #202023;
    color: #e4e4e7;
    selection-background-color: #0284c7;
    border: 1px solid #3f3f46;
}
QCheckBox {
    color: #d4d4d8;
    font-size: 11px;
}
QTabWidget::pane {
    border: 1px solid #3f3f46;
    background-color: #18181b;
}
QTabBar::tab {
    background-color: #27272a;
    color: #a1a1aa;
    padding: 6px 12px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: bold;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: #0284c7;
    color: #ffffff;
}
QTableWidget {
    background-color: #18181b;
    alternate-background-color: #202023;
    color: #e4e4e7;
    gridline-color: #3f3f46;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    font-family: 'Consolas', monospace;
    font-size: 11px;
}
QHeaderView::section {
    background-color: #27272a;
    color: #f4f4f5;
    padding: 3px;
    font-weight: bold;
    border: 1px solid #3f3f46;
    font-size: 11px;
}
QTextEdit {
    background-color: #18181b;
    color: #00f0ff;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    font-family: 'Consolas', monospace;
    font-size: 12px;
}
QStatusBar {
    background-color: #09090b;
    color: #a1a1aa;
    border-top: 1px solid #27272a;
    font-size: 11px;
}
QStatusBar QLabel {
    background-color: transparent;
    background: transparent;
    color: #a1a1aa;
}
QSplitter::handle {
    background-color: #27272a;
}
QSplitter::handle:hover {
    background-color: #00f0ff;
}
QMenuBar {
    background-color: #202023;
    color: #e4e4e7;
    border-bottom: 1px solid #3f3f46;
    font-size: 12px;
}
QMenuBar::item {
    background-color: transparent;
    padding: 5px 10px;
}
QMenuBar::item:selected {
    background-color: #0284c7;
    color: #ffffff;
    border-radius: 2px;
}
QMenuBar::item:pressed {
    background-color: #0369a1;
    color: #ffffff;
}
QMenu {
    background-color: #202023;
    color: #e4e4e7;
    border: 1px solid #3f3f46;
    padding: 4px 0px;
    font-size: 12px;
}
QMenu::item {
    background-color: transparent;
    padding: 6px 28px 6px 16px;
}
QMenu::item:selected {
    background-color: #0284c7;
    color: #ffffff;
}
QMenu::item:disabled {
    color: #71717a;
}
QMenu::separator {
    height: 1px;
    background-color: #3f3f46;
    margin: 4px 8px;
}
QToolTip {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}
QScrollBar:vertical {
    background-color: #18181b;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #3f3f46;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background-color: #71717a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #18181b;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #3f3f46;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #71717a;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


class CaptureWorker(QtCore.QThread):
    """Luồng phụ thu thập dữ liệu serial ngầm không gây block UI."""
    capture_done = QtCore.pyqtSignal(dict)
    capture_error = QtCore.pyqtSignal(str)

    def __init__(self, client: LogicAnalyzerClient, rate_idx: int, trig_ch: int, trig_mode: int):
        super().__init__()
        self.client = client
        self.rate_idx = rate_idx
        self.trig_ch = trig_ch
        self.trig_mode = trig_mode

    def run(self):
        try:
            res = self.client.start_capture(
                rate_idx=self.rate_idx,
                trig_ch=self.trig_ch,
                trig_mode=self.trig_mode
            )
            if res.get("success", False):
                self.capture_done.emit(res)
            else:
                self.capture_error.emit(res.get("error", "Lỗi thu thập dữ liệu"))
        except Exception as e:
            self.capture_error.emit(str(e))


class MainWindow(QtWidgets.QMainWindow):
    """Cửa sổ chính bố cục 3 vùng tối ưu 16:9 phong cách Saleae Logic 2."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HUST Logic Analyzer (8 Channels, 6 MHz) — Lead Dev: Nguyen Van Hoi")
        self.resize(1360, 780)
        self.setMinimumSize(1080, 600)
        self.setStyleSheet(DARK_THEME_CSS)

        # Lớp Client & Worker
        self.client = LogicAnalyzerClient()
        self.worker: Optional[CaptureWorker] = None

        # Bộ giải mã
        self.uart_decoder = UARTDecoder(sample_rate=1_000_000, baudrate=115200)
        self.i2c_decoder = I2CDecoder(sample_rate=1_000_000)
        self.spi_decoder = SPIDecoder(sample_rate=1_000_000)

        # Dữ liệu hiện hành
        self.current_data: Optional[Dict[str, Any]] = None
        self.current_uart_frames: List[Dict[str, Any]] = []
        self.current_i2c_frames: List[Dict[str, Any]] = []
        self.current_spi_frames: List[Dict[str, Any]] = []

        # Khởi tạo 3 Vùng, Menu Bar & Status Bar
        self._init_layout()
        self._init_menu_bar()
        self._refresh_ports()

        # Nạp dữ liệu giả lập ban đầu để sẵn sàng hiển thị sóng ngay khi mở
        sample_file = os.path.join(os.path.dirname(__file__), "..", "tests", "sample_data_1mhz.bin")
        if os.path.exists(sample_file):
            self._load_bin_file(sample_file)

        # Backward compatibility aliases
        self.plot_widget = self.waveform.plot_widget
        self.trigger_line = self.waveform.trigger_line
        self.cursor_manager = self.waveform
        self.hud_widget = self.waveform.hud
        self.txt_decoded = self.txt_uart_decoded
        self.table_frames = self.table_uart_packets
        self.table_uart_frames = self.table_uart_packets
        self.ch_name_edits = self.ch_edits
        self.ch_checkboxes = self.ch_checks
        self.channel_names = self.waveform.channel_names
        self.channel_visible = self.waveform.channel_visible
        self.channel_curves = self.waveform.curves

    def _on_channel_name_changed(self, ch: int):
        new_name = self.ch_edits[ch].text().strip()
        self.waveform.set_channel_name(ch, new_name)

    def _on_channel_visibility_changed(self, ch: int, state):
        visible = (state == QtCore.Qt.Checked or state == 1 or state is True)
        self.waveform.set_channel_visible(ch, visible)

    def _on_decode_uart(self):
        self._decode_uart()

    # =========================================================================
    # THANH BẢNG CHỌN (MENU BAR CHUẨN CÔNG NGHIỆP)
    # =========================================================================

    def _init_menu_bar(self):
        menubar = self.menuBar()

        # Menu File
        menu_file = menubar.addMenu("&File")

        act_open = QtWidgets.QAction("&Open Capture (.bin)...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_capture_file)
        menu_file.addAction(act_open)

        menu_file.addSeparator()

        act_exp_img = QtWidgets.QAction("Export &Image (PNG, SVG)...", self)
        act_exp_img.setShortcut("Ctrl+S")
        act_exp_img.triggered.connect(self._export_image)
        menu_file.addAction(act_exp_img)

        act_exp_csv = QtWidgets.QAction("Export &CSV Data...", self)
        act_exp_csv.setShortcut("Ctrl+E")
        act_exp_csv.triggered.connect(self._export_csv)
        menu_file.addAction(act_exp_csv)

        act_exp_vcd = QtWidgets.QAction("Export &VCD (GTKWave)...", self)
        act_exp_vcd.setShortcut("Ctrl+V")
        act_exp_vcd.triggered.connect(self._export_vcd)
        menu_file.addAction(act_exp_vcd)

        menu_file.addSeparator()

        act_exit = QtWidgets.QAction("E&xit", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # Menu Capture
        menu_capture = menubar.addMenu("&Capture")

        act_start = QtWidgets.QAction("&Start Capture", self)
        act_start.setShortcut("F5")
        act_start.triggered.connect(self._on_start_capture)
        menu_capture.addAction(act_start)

        act_abort = QtWidgets.QAction("&Abort Capture", self)
        act_abort.setShortcut("Escape")
        act_abort.triggered.connect(self._on_abort)
        menu_capture.addAction(act_abort)

        # Menu View
        menu_view = menubar.addMenu("&View")

        act_zoom_fit = QtWidgets.QAction("&Zoom Fit", self)
        act_zoom_fit.setShortcut("Ctrl+F")
        act_zoom_fit.triggered.connect(self.waveform.zoom_fit)
        menu_view.addAction(act_zoom_fit)

        # Menu Help
        menu_help = menubar.addMenu("&Help")

        act_about = QtWidgets.QAction("&About Logic Analyzer", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    def _open_capture_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Raw Capture File", "", "Binary Capture (*.bin);;All Files (*)"
        )
        if path:
            self._load_bin_file(path)

    def _show_about(self):
        QtWidgets.QMessageBox.about(
            self,
            "About HUST Logic Analyzer",
            "<h3>HUST Logic Analyzer (8 Channels, 6 MHz)</h3>"
            "<p>Firmware: STM32F401CCU6 (WeAct Black Pill V3.0)</p>"
            "<p><b>Lead Developer:</b> Nguyen Van Hoi (TV1 - Firmware Engineer)</p>"
            "<p><b>Architecture:</b> 3-Zone Professional Layout (Saleae / DSView Standard)</p>"
            "<p><b>SSoT Protocol:</b> spec/protocol.md (32,776 B Data Frame)</p>"
            "<p>Hanoi University of Science and Technology (HUST) - 2026</p>"
        )

    # =========================================================================
    # BỐ CỤC 3 VÙNG (3-ZONE LAYOUT)
    # =========================================================================

    def _init_layout(self):
        central_widget = QtWidgets.QWidget(self)
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        root_layout = QtWidgets.QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Khởi tạo Waveform Widget (Vùng 2) & Sidebar (Vùng 3) trước
        self.waveform = WaveformWidget(self)
        self.sidebar = self._create_right_sidebar()

        # VÙNG 1: Thanh điều khiển ngang trên cùng (Top Control Bar - Cao đúng 45px - Cố định)
        self.top_bar = self._create_top_control_bar()
        self.top_bar.setFixedHeight(45)
        root_layout.addWidget(self.top_bar)

        # SPLITTER CHÍNH (Vùng 2: 72% | Vùng 3: 28%)
        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.main_splitter.setHandleWidth(5)

        # VÙNG 2: Khung vẽ sóng trung tâm (Waveform Viewport - 72%)
        self.main_splitter.addWidget(self.waveform)

        # VÙNG 3: Cột điều khiển bên phải (Right Sidebar - 28%)
        self.main_splitter.addWidget(self.sidebar)

        # Tỉ lệ 72% và 28%
        self.main_splitter.setStretchFactor(0, 72)
        self.main_splitter.setStretchFactor(1, 28)
        self.main_splitter.setSizes([980, 380])

        root_layout.addWidget(self.main_splitter, 1)

        # VÙNG 4: Thanh trạng thái đáy (Status Bar - Cao 25px)
        self._init_status_bar()

    def _render_capture_data(self, res: Dict[str, Any]):
        """Bí danh tương thích ngược cho việc vẽ dữ liệu."""
        self._on_capture_done(res)

    # =========================================================================
    # VÙNG 1: TOP CONTROL BAR (CHUẨN SALEAE / DSVIEW)
    # =========================================================================

    def _create_top_control_bar(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setObjectName("top_bar")
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)

        # Cụm 1: Cổng kết nối (Port & Connection)
        layout.addWidget(QtWidgets.QLabel("<b>Port:</b>"))
        self.cb_ports = QtWidgets.QComboBox()
        self.cb_ports.setMinimumWidth(150)
        layout.addWidget(self.cb_ports)

        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.setToolTip("Rescan available serial COM / ACM ports")
        self.btn_refresh.clicked.connect(self._refresh_ports)
        layout.addWidget(self.btn_refresh)

        self.btn_connect = QtWidgets.QPushButton("Connect")
        self.btn_connect.clicked.connect(self._on_toggle_connect)
        layout.addWidget(self.btn_connect)

        self.lbl_led = QtWidgets.QLabel("●")
        self.lbl_led.setStyleSheet("color: #ef4444; font-size: 15px; background: transparent;")
        layout.addWidget(self.lbl_led)

        # Phân cách 1
        sep1 = QtWidgets.QFrame()
        sep1.setFixedWidth(1)
        sep1.setStyleSheet("background-color: #3f3f46; border: none; margin-top: 6px; margin-bottom: 6px;")
        layout.addWidget(sep1)

        # Cụm 2: Cấu hình lấy mẫu & Trigger (Sample Rate & Trigger Settings)
        layout.addWidget(QtWidgets.QLabel("<b>Rate:</b>"))
        self.cb_rate = QtWidgets.QComboBox()
        for item in self.client.RATE_TABLE:
            self.cb_rate.addItem(item["label"], item["idx"])
        self.cb_rate.setCurrentIndex(3)  # Mặc định 1 MHz
        layout.addWidget(self.cb_rate)

        layout.addWidget(QtWidgets.QLabel("<b>Channel:</b>"))
        self.cb_trig_ch = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_trig_ch.addItem(f"CH{ch}", ch)
        self.cb_trig_ch.setCurrentIndex(0)
        layout.addWidget(self.cb_trig_ch)

        layout.addWidget(QtWidgets.QLabel("<b>Trigger:</b>"))
        self.cb_trig_mode = QtWidgets.QComboBox()
        for tm in self.client.TRIG_MODES:
            self.cb_trig_mode.addItem(tm["name"], tm["mode"])
        self.cb_trig_mode.setCurrentIndex(2)  # Mặc định Falling Edge
        layout.addWidget(self.cb_trig_mode)

        # Phân cách 2
        sep2 = QtWidgets.QFrame()
        sep2.setFixedWidth(1)
        sep2.setStyleSheet("background-color: #3f3f46; border: none; margin-top: 6px; margin-bottom: 6px;")
        layout.addWidget(sep2)

        # Cụm 3: Nút hành động chính (Start Capture / Abort)
        self.btn_start = QtWidgets.QPushButton("Start Capture")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self._on_start_capture)
        layout.addWidget(self.btn_start)

        self.btn_abort = QtWidgets.QPushButton("Abort")
        self.btn_abort.setObjectName("btn_abort")
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self._on_abort)
        layout.addWidget(self.btn_abort)

        # Cụm 4: Checkbox Offline Mock & Zoom Fit
        self.chk_mock = QtWidgets.QCheckBox("Offline Mock")
        self.chk_mock.setToolTip("Run with offline mock sample buffer without hardware kit")
        layout.addWidget(self.chk_mock)

        self.btn_zoom_fit = QtWidgets.QPushButton("Zoom Fit")
        self.btn_zoom_fit.clicked.connect(self.waveform.zoom_fit)
        layout.addWidget(self.btn_zoom_fit)

        layout.addStretch()
        return frame

    # =========================================================================
    # VÙNG 3: RIGHT SIDEBAR (DECODERS & EXPORT TOOLS)
    # =========================================================================

    def _create_right_sidebar(self) -> QtWidgets.QFrame:
        container = QtWidgets.QFrame()
        container.setObjectName("sidebar_container")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        tab_widget = QtWidgets.QTabWidget()

        # Tab 1: Protocol Decoder & Packet Table
        tab_decoder = self._create_tab_decoder()
        tab_widget.addTab(tab_decoder, "Protocol Decoders")

        # Tab 2: Export & Tools
        tab_tools = self._create_tab_tools()
        tab_widget.addTab(tab_tools, "Export & Channels")

        layout.addWidget(tab_widget)
        return container

    def _create_tab_decoder(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(6, 8, 6, 6)
        layout.setSpacing(8)

        # Protocol Selector
        proto_row = QtWidgets.QHBoxLayout()
        proto_row.addWidget(QtWidgets.QLabel("<b>Protocol:</b>"))
        self.cb_protocol = QtWidgets.QComboBox()
        self.cb_protocol.addItems(["UART (Serial)", "I2C (Bus)", "SPI (Bus)"])
        self.cb_protocol.currentIndexChanged.connect(self._on_protocol_changed)
        proto_row.addWidget(self.cb_protocol, 1)

        self.btn_run_decode = QtWidgets.QPushButton("Decode")
        self.btn_run_decode.setStyleSheet("background-color: #0284c7; font-weight: bold;")
        self.btn_run_decode.clicked.connect(self._on_run_decoder)
        proto_row.addWidget(self.btn_run_decode)
        layout.addLayout(proto_row)

        # Stacked options container cho từng giao thức
        self.stack_options = QtWidgets.QStackedWidget()

        # Options UART
        uart_box = QtWidgets.QFrame()
        uart_lay = QtWidgets.QHBoxLayout(uart_box)
        uart_lay.setContentsMargins(0, 0, 0, 0)
        uart_lay.addWidget(QtWidgets.QLabel("Channel:"))
        self.cb_u_ch = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_u_ch.addItem(f"D{ch}", ch)
        uart_lay.addWidget(self.cb_u_ch)

        uart_lay.addWidget(QtWidgets.QLabel("Baud Rate:"))
        self.cb_u_baud = QtWidgets.QComboBox()
        for b in [115200, 9600, 19200, 38400, 57600, 230400, 460800, 921600]:
            self.cb_u_baud.addItem(f"{b:,} bps", b)
        uart_lay.addWidget(self.cb_u_baud)
        self.stack_options.addWidget(uart_box)

        # Options I2C
        i2c_box = QtWidgets.QFrame()
        i2c_lay = QtWidgets.QHBoxLayout(i2c_box)
        i2c_lay.setContentsMargins(0, 0, 0, 0)
        i2c_lay.addWidget(QtWidgets.QLabel("SCL:"))
        self.cb_i_scl = QtWidgets.QComboBox()
        self.cb_i_sda = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_i_scl.addItem(f"D{ch}", ch)
            self.cb_i_sda.addItem(f"D{ch}", ch)
        self.cb_i_scl.setCurrentIndex(1)
        self.cb_i_sda.setCurrentIndex(2)
        i2c_lay.addWidget(self.cb_i_scl)
        i2c_lay.addWidget(QtWidgets.QLabel("SDA:"))
        i2c_lay.addWidget(self.cb_i_sda)
        self.stack_options.addWidget(i2c_box)

        # Options SPI
        spi_box = QtWidgets.QFrame()
        spi_lay = QtWidgets.QHBoxLayout(spi_box)
        spi_lay.setContentsMargins(0, 0, 0, 0)
        spi_lay.addWidget(QtWidgets.QLabel("SCK:"))
        self.cb_s_sck = QtWidgets.QComboBox()
        self.cb_s_mosi = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_s_sck.addItem(f"D{ch}", ch)
            self.cb_s_mosi.addItem(f"D{ch}", ch)
        self.cb_s_sck.setCurrentIndex(5)
        self.cb_s_mosi.setCurrentIndex(3)
        spi_lay.addWidget(self.cb_s_sck)
        spi_lay.addWidget(QtWidgets.QLabel("MOSI:"))
        spi_lay.addWidget(self.cb_s_mosi)
        self.stack_options.addWidget(spi_box)

        layout.addWidget(self.stack_options)

        # Bảng danh sách gói tin (Packet Table) - Bấm để Zoom
        layout.addWidget(QtWidgets.QLabel("<b>Packet Table (Click row to zoom):</b>"))
        self.table_packets = QtWidgets.QTableWidget(0, 4)
        self.table_packets.setHorizontalHeaderLabels(["#", "Time (ms)", "Decoded", "Hex Data"])
        self.table_packets.horizontalHeader().setStretchLastSection(True)
        self.table_packets.setColumnWidth(0, 45)
        self.table_packets.setColumnWidth(1, 95)
        self.table_packets.setColumnWidth(2, 90)
        self.table_packets.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_packets.setAlternatingRowColors(True)
        self.table_packets.cellClicked.connect(self._on_packet_clicked)
        layout.addWidget(self.table_packets, 2)

        # Cửa sổ Terminal văn bản
        layout.addWidget(QtWidgets.QLabel("<b>Decoded Output:</b>"))
        self.txt_terminal = QtWidgets.QTextEdit()
        self.txt_terminal.setReadOnly(True)
        layout.addWidget(self.txt_terminal, 1)

        # Aliases
        self.table_uart_packets = self.table_packets
        self.txt_uart_decoded = self.txt_terminal

        return widget

    def _create_tab_tools(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(10)

        # Cụm 1: Xuất dữ liệu
        grp_export = QtWidgets.QGroupBox("Export Data")
        exp_layout = QtWidgets.QVBoxLayout(grp_export)
        exp_layout.setSpacing(8)

        btn_exp_img = QtWidgets.QPushButton("Export Image (PNG, SVG)...")
        btn_exp_img.clicked.connect(self._export_image)
        exp_layout.addWidget(btn_exp_img)

        btn_exp_csv = QtWidgets.QPushButton("Export CSV Data...")
        btn_exp_csv.clicked.connect(self._export_csv)
        exp_layout.addWidget(btn_exp_csv)

        btn_exp_vcd = QtWidgets.QPushButton("Export VCD (GTKWave)...")
        btn_exp_vcd.clicked.connect(self._export_vcd)
        exp_layout.addWidget(btn_exp_vcd)

        layout.addWidget(grp_export)

        # Cụm 2: Quản lý 8 kênh (Bật/Tắt & Đổi tên)
        grp_ch = QtWidgets.QGroupBox("Channels")
        ch_layout = QtWidgets.QVBoxLayout(grp_ch)
        ch_layout.setSpacing(4)

        self.ch_checks = []
        self.ch_edits = []

        for ch in range(8):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(6)

            chk = QtWidgets.QCheckBox()
            chk.setChecked(True)
            chk.setStyleSheet(f"QCheckBox::indicator:checked {{ background-color: {NEON_CHANNEL_COLORS[ch]}; border: 1px solid #fff; }}")
            chk.stateChanged.connect(lambda state, c=ch: self.waveform.set_channel_visible(c, state == QtCore.Qt.Checked))
            self.ch_checks.append(chk)

            edit = QtWidgets.QLineEdit(self.waveform.channel_names[ch])
            edit.setStyleSheet(f"background-color: #18181b; color: {NEON_CHANNEL_COLORS[ch]}; border: 1px solid #3f3f46; border-radius: 3px; padding: 2px 4px; font-weight: bold;")
            edit.editingFinished.connect(lambda c=ch: self.waveform.set_channel_name(c, self.ch_edits[c].text().strip()))
            self.ch_edits.append(edit)

            row.addWidget(chk)
            row.addWidget(edit, 1)
            ch_layout.addLayout(row)

        layout.addWidget(grp_ch)
        layout.addStretch()
        return widget

    # =========================================================================
    # VÙNG 4: STATUS BAR (CAO 25PX)
    # =========================================================================

    def _init_status_bar(self):
        sb = self.statusBar()
        sb.setFixedHeight(25)

        self.sb_conn = QtWidgets.QLabel("Port: Disconnected")
        self.sb_rate = QtWidgets.QLabel("Rate: 1.00 MHz")
        self.sb_samples = QtWidgets.QLabel("Samples: 0 / 32,768")
        self.sb_status = QtWidgets.QLabel("Status: IDLE")
        self.sb_csum = QtWidgets.QLabel("Checksum: --")
        self.sb_fps = QtWidgets.QLabel("FPS: 60")

        sb.addWidget(self.sb_conn, 2)
        sb.addWidget(self.sb_rate, 2)
        sb.addWidget(self.sb_samples, 2)
        sb.addWidget(self.sb_status, 3)
        sb.addWidget(self.sb_csum, 2)
        sb.addPermanentWidget(self.sb_fps)

    # =========================================================================
    # LOGIC KẾT NỐI & THU THẬP
    # =========================================================================

    def _refresh_ports(self):
        self.cb_ports.clear()
        ports = self.client.list_ports()
        for dev, desc in ports:
            self.cb_ports.addItem(desc, dev)

        # Tự động chọn ttyACM0 nếu có
        for i in range(self.cb_ports.count()):
            val = str(self.cb_ports.itemData(i))
            if "ttyACM" in val or "STM32" in val:
                self.cb_ports.setCurrentIndex(i)
                break

    def _on_toggle_connect(self):
        if self.client.is_connected:
            self.client.disconnect()
            self._update_conn_ui(False, "Disconnected")
        else:
            if self.chk_mock.isChecked():
                port = "OFFLINE_MOCK"
            else:
                port = self.cb_ports.currentData()

            if not port:
                QtWidgets.QMessageBox.warning(self, "Warning", "Please select a serial port or enable Offline Mock!")
                return

            ok, msg = self.client.connect(port)
            if ok:
                ok_p, ver = self.client.ping()
                desc = f"{port} ({ver if ok_p else 'v1.0.0'})"
                self._update_conn_ui(True, desc)
            else:
                self._update_conn_ui(False, msg)
                QtWidgets.QMessageBox.critical(self, "Connection Error", msg)

    def _update_conn_ui(self, connected: bool, desc: str):
        if connected:
            self.btn_connect.setText("Disconnect")
            self.lbl_led.setStyleSheet("color: #10b981; font-size: 15px; background: transparent;")
            self.sb_conn.setText(f"Port: {desc}")
        else:
            self.btn_connect.setText("Connect")
            self.lbl_led.setStyleSheet("color: #ef4444; font-size: 15px; background: transparent;")
            self.sb_conn.setText("Port: Disconnected")

    def _on_start_capture(self):
        # Tự động kết nối nếu đang tick Offline Mock
        if not self.client.is_connected:
            if self.chk_mock.isChecked():
                self.client.connect("OFFLINE_MOCK")
                self._update_conn_ui(True, "Offline Mock")
            else:
                QtWidgets.QMessageBox.warning(self, "Not Connected", "Please connect to a device or enable Offline Mock first!")
                return

        rate_idx = self.cb_rate.currentData()
        trig_ch = self.cb_trig_ch.currentData()
        trig_mode = self.cb_trig_mode.currentData()

        self.btn_start.setEnabled(False)
        self.btn_abort.setEnabled(True)
        self.sb_status.setText("Status: Capturing...")

        self.worker = CaptureWorker(self.client, rate_idx, trig_ch, trig_mode)
        self.worker.capture_done.connect(self._on_capture_done)
        self.worker.capture_error.connect(self._on_capture_error)
        self.worker.start()

    def _on_abort(self):
        self.client.abort()
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self.sb_status.setText("Status: Aborted")

    def _on_capture_done(self, res: Dict[str, Any]):
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self.current_data = res

        # 1. Vẽ sóng lên Viewport Vùng 2
        self.waveform.render_data(res)

        # 2. Cập nhật Status Bar Vùng 4
        sample_count = res["sample_count"]
        sample_rate = res["sample_rate"]
        elapsed_s = res.get("elapsed_s", 0.0)
        self.sb_rate.setText(f"Rate: {sample_rate/1e6:.2f} MHz")
        self.sb_samples.setText(f"Samples: {sample_count:,} / 32,768")
        self.sb_status.setText(f"Status: {res['status_name']} ({elapsed_s:.3f} s)")
        csum_byte = res.get("payload")[0] if len(res.get("payload", [])) else 0
        self.sb_csum.setText(f"Checksum: {'PASS (0x%02X)' % csum_byte if res['checksum_ok'] else 'FAIL'}")

        # 3. Tự động chạy bộ giải mã hiện đang chọn
        self._on_run_decoder()

    def _on_capture_error(self, err: str):
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self.sb_status.setText(f"Error: {err}")
        QtWidgets.QMessageBox.warning(self, "Capture Error", err)

    def _load_bin_file(self, filepath: str):
        res = self.client.load_offline_file(filepath)
        if res.get("success"):
            self._on_capture_done(res)
            self.sb_conn.setText(f"File: {os.path.basename(filepath)}")

    # =========================================================================
    # GIẢI MÃ & BẢNG GÓI TIN (DECODER & PACKET TABLE)
    # =========================================================================

    def _on_protocol_changed(self, idx: int):
        self.stack_options.setCurrentIndex(idx)
        self._on_run_decoder()

    def _on_run_decoder(self):
        if not self.current_data:
            return

        idx = self.cb_protocol.currentIndex()
        if idx == 0:
            self._decode_uart()
        elif idx == 1:
            self._decode_i2c()
        elif idx == 2:
            self._decode_spi()

    def _decode_uart(self):
        ch = self.cb_u_ch.currentData()
        baud = self.cb_u_baud.currentData()
        sample_rate = self.current_data["sample_rate"]
        ch_arr = self.current_data["channels"][ch]

        self.uart_decoder.sample_rate = sample_rate
        self.uart_decoder.baudrate = baud

        text, frames = self.uart_decoder.decode(ch_arr.tolist(), start_idx=0)
        self.current_uart_frames = frames

        # Hiển thị Terminal
        if text:
            self.txt_terminal.setPlainText(text)
        else:
            num_ones = int(np.count_nonzero(ch_arr == 1))
            transitions = int(np.count_nonzero(np.diff(ch_arr) != 0))
            if transitions == 0 and num_ones == 0:
                self.txt_terminal.setHtml(f'<span style="color: #fbbf24;">[WARNING: Channel D{ch} is at continuous LOW (0V). Connect jumper wire from PA9 to PA0 for loopback self-test!]</span>')
            elif transitions == 0:
                self.txt_terminal.setHtml(f'<span style="color: #fbbf24;">[WARNING: Channel D{ch} is at continuous HIGH (3.3V IDLE). No signal transitions detected.]</span>')
            else:
                self.txt_terminal.setHtml(f'<span style="color: #fbbf24;">[WARNING: Detected {transitions} transitions but could not decode valid frame. Check Baud Rate ({baud:,} bps).]</span>')

        # Điền bảng Packets
        self.table_packets.setRowCount(len(frames))
        for row, f in enumerate(frames):
            t_ms = f["start_time_s"] * 1000.0
            it0 = QtWidgets.QTableWidgetItem(str(row + 1))
            it0.setTextAlignment(QtCore.Qt.AlignCenter)
            it1 = QtWidgets.QTableWidgetItem(f"{t_ms:.3f} ms")
            it1.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            it2 = QtWidgets.QTableWidgetItem(repr(f["char"])[1:-1])
            it2.setTextAlignment(QtCore.Qt.AlignCenter)
            it3 = QtWidgets.QTableWidgetItem(f"0x{f['byte_val']:02X}")
            it3.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table_packets.setItem(row, 0, it0)
            self.table_packets.setItem(row, 1, it1)
            self.table_packets.setItem(row, 2, it2)
            self.table_packets.setItem(row, 3, it3)

    def _decode_i2c(self):
        scl_ch = self.cb_i_scl.currentData()
        sda_ch = self.cb_i_sda.currentData()
        scl = self.current_data["channels"][scl_ch].tolist()
        sda = self.current_data["channels"][sda_ch].tolist()
        self.i2c_decoder.sample_rate = self.current_data["sample_rate"]

        text, frames = self.i2c_decoder.decode(scl, sda)
        self.current_i2c_frames = frames
        if text:
            self.txt_terminal.setPlainText(text)
        else:
            self.txt_terminal.setHtml('<span style="color: #fbbf24;">[No valid I2C bus events detected]</span>')

        self.table_packets.setRowCount(len(frames))
        for row, f in enumerate(frames):
            t_ms = f["start_time_s"] * 1000.0
            it0 = QtWidgets.QTableWidgetItem(str(row + 1))
            it0.setTextAlignment(QtCore.Qt.AlignCenter)
            it1 = QtWidgets.QTableWidgetItem(f"{t_ms:.3f} ms")
            it1.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            it2 = QtWidgets.QTableWidgetItem(f["type"])
            it2.setTextAlignment(QtCore.Qt.AlignCenter)
            it3 = QtWidgets.QTableWidgetItem(f["desc"])
            it3.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.table_packets.setItem(row, 0, it0)
            self.table_packets.setItem(row, 1, it1)
            self.table_packets.setItem(row, 2, it2)
            self.table_packets.setItem(row, 3, it3)

    def _decode_spi(self):
        sck_ch = self.cb_s_sck.currentData()
        mosi_ch = self.cb_s_mosi.currentData()
        sck = self.current_data["channels"][sck_ch].tolist()
        mosi = self.current_data["channels"][mosi_ch].tolist()
        self.spi_decoder.sample_rate = self.current_data["sample_rate"]

        text, frames = self.spi_decoder.decode(sck, mosi)
        self.current_spi_frames = frames
        if text:
            self.txt_terminal.setPlainText(text)
        else:
            self.txt_terminal.setHtml('<span style="color: #fbbf24;">[No valid SPI bus data detected]</span>')

        self.table_packets.setRowCount(len(frames))
        for row, f in enumerate(frames):
            t_ms = f["start_time_s"] * 1000.0
            it0 = QtWidgets.QTableWidgetItem(str(row + 1))
            it0.setTextAlignment(QtCore.Qt.AlignCenter)
            it1 = QtWidgets.QTableWidgetItem(f"{t_ms:.3f} ms")
            it1.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            it2 = QtWidgets.QTableWidgetItem(f["mosi_ascii"])
            it2.setTextAlignment(QtCore.Qt.AlignCenter)
            it3 = QtWidgets.QTableWidgetItem(f["mosi_hex"])
            it3.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table_packets.setItem(row, 0, it0)
            self.table_packets.setItem(row, 1, it1)
            self.table_packets.setItem(row, 2, it2)
            self.table_packets.setItem(row, 3, it3)

    def _on_packet_clicked(self, row: int, col: int):
        """Click một dòng trong bảng gói tin -> Tự động Pan/Zoom tới vị trí đó trên đồ thị."""
        proto = self.cb_protocol.currentIndex()
        if proto == 0 and hasattr(self, "current_uart_frames") and 0 <= row < len(self.current_uart_frames):
            f = self.current_uart_frames[row]
            self.waveform.zoom_to_window(f["start_time_s"], f["stop_time_s"])
        elif proto == 1 and hasattr(self, "current_i2c_frames") and 0 <= row < len(self.current_i2c_frames):
            f = self.current_i2c_frames[row]
            self.waveform.zoom_to_window(f["start_time_s"], f["stop_time_s"])
        elif proto == 2 and hasattr(self, "current_spi_frames") and 0 <= row < len(self.current_spi_frames):
            f = self.current_spi_frames[row]
            self.waveform.zoom_to_window(f["start_time_s"], f["stop_time_s"])

    # =========================================================================
    # XUẤT TỆP (EXPORTER)
    # =========================================================================

    def _export_image(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Waveform Image", "waveform.png", "PNG Image (*.png);;SVG Vector (*.svg)")
        if path:
            if export_image(self.waveform.plot_widget, path):
                QtWidgets.QMessageBox.information(self, "Success", f"Waveform image exported successfully:\n{path}")

    def _export_csv(self):
        if not self.current_data:
            QtWidgets.QMessageBox.warning(self, "No Data", "No capture data available to export!")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export CSV Data", "logic_data.csv", "CSV Spreadsheet (*.csv)")
        if path:
            if export_csv(self.current_data, path):
                QtWidgets.QMessageBox.information(self, "Success", f"Exported 32,768 samples to:\n{path}")

    def _export_vcd(self):
        if not self.current_data:
            QtWidgets.QMessageBox.warning(self, "No Data", "No capture data available to export!")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export VCD File", "waveform.vcd", "VCD Value Change Dump (*.vcd)")
        if path:
            if export_vcd(self.current_data, path):
                QtWidgets.QMessageBox.information(self, "Success", f"VCD file exported successfully:\n{path}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
