#!/usr/bin/env python3
"""
software/gui/main_window.py
Giao diện người dùng Desktop (PyQt5 + pyqtgraph) cho STM32 8-Channel 6MHz Logic Analyzer.
Thiết kế Dark Mode cao cấp chuẩn thương mại (phong cách Saleae Logic 2 / DSView / PulseView).

Tích hợp toàn diện:
1. Control Panel: Cổng COM / USB-CDC (hỗ trợ Offline Mock), Tần số lấy mẫu (10 kHz - 6 MHz), Trigger (Free-run, Rising, Falling), Start/Abort capture.
2. Waveform Viewer: 8 kênh số neon xếp tầng 60 FPS, trục thời gian t=0 tại điểm Trigger, Pre-trigger âm (-t), Post-trigger dương (+t).
3. Thước đo thời gian (Cursors A & B): Kéo thả trực tiếp, HUD hiển thị thời gian thực t_A, t_B, Δt và tần số f = 1/Δt.
4. Channel Manager: Bật/tắt từng kênh, nhấp đúp đổi tên kênh (ví dụ: D0 -> UART_TX, D1 -> SCL, D2 -> SDA).
5. Bộ giải mã đa giao thức (Tabbed Protocol Decoders):
   - Tab 1: UART Decoder (Baudrate tùy biến, ASCII output, Frame inspector).
   - Tab 2: I2C Decoder (SCL, SDA, START, 7-bit Addr, R/W, ACK/NACK, DATA, STOP).
   - Tab 3: SPI Decoder (SCK, MOSI, MISO, CS, 4 Chế độ CPOL/CPHA).
6. Xuất dữ liệu đa định dạng: Ảnh PNG/SVG sắc nét, Bảng tính CSV, Tệp xung số VCD (GTKWave).
"""

import os
import sys
import time
import numpy as np
from typing import Optional, Dict, Any, List

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from software.gui.logic_client import LogicAnalyzerClient
from software.decoders.uart_decoder import UARTDecoder
from software.decoders.i2c_decoder import I2CDecoder
from software.decoders.spi_decoder import SPIDecoder
from software.gui.cursors import CursorManager, CursorHUDWidget, format_time, format_freq
from software.utils.exporter import export_image, export_csv, export_vcd


# 8 màu sắc Neon tương phản cao cho 8 kênh logic (D0 đến D7)
CHANNEL_COLORS = [
    "#00e5ff",  # D0: Cyan
    "#ff9100",  # D1: Orange
    "#76ff03",  # D2: Lime
    "#ffd600",  # D3: Yellow
    "#e040fb",  # D4: Purple
    "#00e676",  # D5: Bright Green
    "#ff5252",  # D6: Red/Coral
    "#448aff",  # D7: Electric Blue
]

DEFAULT_CHANNEL_NAMES = [
    "D0 (UART_TX)",
    "D1 (SCL)",
    "D2 (SDA)",
    "D3 (MOSI)",
    "D4 (MISO)",
    "D5 (SCK)",
    "D6 (CS)",
    "D7",
]

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #2d2d30;
    color: #e0e0e0;
    border-bottom: 1px solid #3e3e42;
}
QMenuBar::item {
    background-color: transparent;
    padding: 4px 10px;
}
QMenuBar::item:selected {
    background-color: #3e3e42;
    color: #00e5ff;
}
QMenu {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
}
QMenu::item:selected {
    background-color: #0e639c;
    color: #ffffff;
}
QGroupBox {
    border: 1px solid #3e3e42;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
}
QPushButton {
    background-color: #2d2d30;
    color: #ffffff;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #3e3e42;
    border-color: #007acc;
}
QPushButton:pressed {
    background-color: #0e639c;
}
QPushButton:disabled {
    background-color: #252526;
    color: #656565;
    border-color: #2d2d30;
}
QPushButton#btn_start {
    background-color: #107c41;
    border-color: #107c41;
    font-weight: bold;
    font-size: 13px;
    padding: 7px 16px;
}
QPushButton#btn_start:hover {
    background-color: #138749;
}
QPushButton#btn_abort {
    background-color: #a80000;
    border-color: #a80000;
    font-weight: bold;
    font-size: 13px;
    padding: 7px 16px;
}
QPushButton#btn_abort:hover {
    background-color: #c40000;
}
QComboBox {
    background-color: #2d2d30;
    color: #ffffff;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 5px 8px;
    min-width: 90px;
}
QComboBox:hover {
    border-color: #007acc;
}
QComboBox QAbstractItemView {
    background-color: #252526;
    color: #cccccc;
    selection-background-color: #0e639c;
    border: 1px solid #3e3e42;
}
QTabWidget::pane {
    border: 1px solid #3e3e42;
    background-color: #252526;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #2d2d30;
    color: #aaaaaa;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #0e639c;
    color: #ffffff;
}
QTableWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    gridline-color: #2d2d30;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    selection-background-color: #0e639c;
}
QHeaderView::section {
    background-color: #2d2d30;
    color: #ffffff;
    padding: 4px;
    font-weight: bold;
    border: 1px solid #3e3e42;
}
QTextEdit {
    background-color: #1e1e1e;
    color: #00e5ff;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    font-family: 'Consolas', 'DejaVu Sans Mono', monospace;
    font-size: 13px;
}
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
    font-weight: 500;
}
"""


class CaptureWorker(QtCore.QThread):
    """Luồng chạy nền thu thập dữ liệu serial không làm đơ giao diện chính."""
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
                self.capture_error.emit(res.get("error", "Lỗi thu thập dữ liệu không xác định"))
        except Exception as e:
            self.capture_error.emit(f"Ngoại lệ khi thu thập: {e}")


class MainWindow(QtWidgets.QMainWindow):
    """Cửa sổ chính của ứng dụng Logic Analyzer Desktop Client."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HUST Logic Analyzer (8 Channels, 6 MHz) — Lead Dev: Nguyen Van Hoi")
        self.resize(1340, 860)
        self.setMinimumSize(1000, 680)

        self.setStyleSheet(DARK_STYLESHEET)
        pg.setConfigOption("background", "#181818")
        pg.setConfigOption("foreground", "#cccccc")
        pg.setConfigOptions(antialias=False)  # Tắt antialias để tối đa hóa FPS đồ thị số

        # Lớp Client điều khiển MCU STM32
        self.client = LogicAnalyzerClient()
        self.capture_worker: Optional[CaptureWorker] = None

        # Các bộ giải mã giao thức
        self.uart_decoder = UARTDecoder(sample_rate=1_000_000, baudrate=115200)
        self.i2c_decoder = I2CDecoder(sample_rate=1_000_000)
        self.spi_decoder = SPIDecoder(sample_rate=1_000_000)

        # Dữ liệu đo kiểm hiện hành
        self.current_data: Optional[Dict[str, Any]] = None
        self.channel_names = list(DEFAULT_CHANNEL_NAMES)
        self.channel_visible = [True] * 8
        self.current_frames: List[Dict[str, Any]] = []

        # Khởi tạo giao diện
        self._init_menu_bar()
        self._init_ui()
        self._refresh_ports()

        # Aliases tương thích ngược
        self.txt_decoded = self.txt_uart_decoded
        self.table_frames = self.table_uart_frames
        self.decoder = self.uart_decoder

        # Nạp dữ liệu giả lập ban đầu để sẵn sàng hiển thị
        sample_file = os.path.join(os.path.dirname(__file__), "..", "tests", "sample_data_1mhz.bin")
        if os.path.exists(sample_file):
            self._load_bin_file(sample_file)

    # =========================================================================
    # MENU BAR
    # =========================================================================

    def _init_menu_bar(self):
        """Khởi tạo thanh Menu Bar chuyên nghiệp."""
        menubar = self.menuBar()

        # Menu File
        file_menu = menubar.addMenu("&File")

        act_open_bin = QtWidgets.QAction("📂 Nạp File Dữ Liệu .BIN...", self)
        act_open_bin.setShortcut("Ctrl+O")
        act_open_bin.triggered.connect(self._on_browse_bin)
        file_menu.addAction(act_open_bin)

        file_menu.addSeparator()

        act_export_png = QtWidgets.QAction("🖼️ Xuất Ảnh Dạng Sóng (PNG/SVG)...", self)
        act_export_png.setShortcut("Ctrl+S")
        act_export_png.triggered.connect(self._on_export_image)
        file_menu.addAction(act_export_png)

        act_export_csv = QtWidgets.QAction("📊 Xuất Bảng Tính (CSV)...", self)
        act_export_csv.setShortcut("Ctrl+E")
        act_export_csv.triggered.connect(self._on_export_csv)
        file_menu.addAction(act_export_csv)

        act_export_vcd = QtWidgets.QAction("⚡ Xuất Định Dạng GTKWave (VCD)...", self)
        act_export_vcd.setShortcut("Ctrl+V")
        act_export_vcd.triggered.connect(self._on_export_vcd)
        file_menu.addAction(act_export_vcd)

        file_menu.addSeparator()

        act_exit = QtWidgets.QAction("❌ Thoát", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Menu View
        view_menu = menubar.addMenu("&View")

        act_toggle_cursors = QtWidgets.QAction("📐 Bật/Tắt Cặp Thước Đo", self)
        act_toggle_cursors.setShortcut("Ctrl+T")
        act_toggle_cursors.triggered.connect(self._toggle_cursors)
        view_menu.addAction(act_toggle_cursors)

        act_zoom_fit = QtWidgets.QAction("🔍 Khôi Phục Toàn Cảnh (Zoom Fit)", self)
        act_zoom_fit.setShortcut("Ctrl+F")
        act_zoom_fit.triggered.connect(self._zoom_fit)
        view_menu.addAction(act_zoom_fit)

        # Menu Help
        help_menu = menubar.addMenu("&Help")
        act_about = QtWidgets.QAction("ℹ️ Giới Thiệu Đề Tài", self)
        act_about.triggered.connect(self._show_about_dialog)
        help_menu.addAction(act_about)

    # =========================================================================
    # GIAO DIỆN CHÍNH (UI LAYOUT)
    # =========================================================================

    def _init_ui(self):
        """Khởi tạo toàn bộ các thành phần giao diện."""
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(6)

        # 1. Top Control Bar (Cấu hình cổng & lấy mẫu)
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel)

        # 2. Main Content Splitter (Waveform Viewer trên + Decoders dưới)
        content_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        content_splitter.setHandleWidth(6)

        # Waveform Container (Kèm Channel Manager và Cursors HUD)
        waveform_container = self._create_waveform_container()
        content_splitter.addWidget(waveform_container)

        # Decoder & Protocol Terminal Panel (Tabbed: UART, I2C, SPI)
        decoder_panel = self._create_decoder_panel()
        content_splitter.addWidget(decoder_panel)

        content_splitter.setStretchFactor(0, 68)
        content_splitter.setStretchFactor(1, 32)
        main_layout.addWidget(content_splitter)

        # 3. Status Bar
        self._init_status_bar()

    def _create_control_panel(self) -> QtWidgets.QWidget:
        """Tạo thanh công cụ điều khiển đỉnh giao diện."""
        panel = QtWidgets.QFrame()
        panel.setStyleSheet("background-color: #252526; border-radius: 6px; padding: 3px;")
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Group 1: Kết nối COM / USB
        lbl_conn = QtWidgets.QLabel("<b>Cổng:</b>")
        self.cb_ports = QtWidgets.QComboBox()
        self.cb_ports.setMinimumWidth(180)

        self.btn_refresh = QtWidgets.QPushButton("↻")
        self.btn_refresh.setToolTip("Quét lại danh sách cổng serial")
        self.btn_refresh.clicked.connect(self._refresh_ports)

        self.btn_connect = QtWidgets.QPushButton("Kết Nối")
        self.btn_connect.clicked.connect(self._on_toggle_connect)

        self.lbl_conn_status = QtWidgets.QLabel("●")
        self.lbl_conn_status.setStyleSheet("color: #ff5252; font-size: 16px;")
        self.lbl_conn_status.setToolTip("Chưa kết nối")

        layout.addWidget(lbl_conn)
        layout.addWidget(self.cb_ports)
        layout.addWidget(self.btn_refresh)
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.lbl_conn_status)

        # Đường phân cách
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.VLine)
        sep1.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep1)

        # Group 2: Tham số lấy mẫu & Trigger
        lbl_rate = QtWidgets.QLabel("<b>Tần Số:</b>")
        self.cb_rate = QtWidgets.QComboBox()
        for item in self.client.RATE_TABLE:
            self.cb_rate.addItem(item["label"], item["idx"])
        self.cb_rate.setCurrentIndex(3)  # Mặc định 1 MHz (ARR=83)

        lbl_trig_ch = QtWidgets.QLabel("<b>Kênh:</b>")
        self.cb_trig_ch = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_trig_ch.addItem(f"CH{ch}", ch)
        self.cb_trig_ch.setCurrentIndex(0)

        lbl_trig_mode = QtWidgets.QLabel("<b>Trigger:</b>")
        self.cb_trig_mode = QtWidgets.QComboBox()
        for tm in self.client.TRIG_MODES:
            self.cb_trig_mode.addItem(tm["name"], tm["mode"])
        self.cb_trig_mode.setCurrentIndex(2)  # Mặc định Falling Edge (Cạnh xuống)

        layout.addWidget(lbl_rate)
        layout.addWidget(self.cb_rate)
        layout.addWidget(lbl_trig_ch)
        layout.addWidget(self.cb_trig_ch)
        layout.addWidget(lbl_trig_mode)
        layout.addWidget(self.cb_trig_mode)

        # Đường phân cách
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.VLine)
        sep2.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep2)

        # Group 3: Nút điều khiển chính
        self.btn_start = QtWidgets.QPushButton("▶ START CAPTURE")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self._on_start_capture)

        self.btn_abort = QtWidgets.QPushButton("⏹ ABORT")
        self.btn_abort.setObjectName("btn_abort")
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self._on_abort)

        self.btn_cursors = QtWidgets.QPushButton("📐 Thước Đo")
        self.btn_cursors.setToolTip("Bật / Tắt Cặp Thước Đo Thời Gian A & B")
        self.btn_cursors.clicked.connect(self._toggle_cursors)

        self.btn_zoom_fit = QtWidgets.QPushButton("🔍 Zoom Fit")
        self.btn_zoom_fit.setToolTip("Khôi phục tầm nhìn toàn bộ dữ liệu mẫu")
        self.btn_zoom_fit.clicked.connect(self._zoom_fit)

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_abort)
        layout.addWidget(self.btn_cursors)
        layout.addWidget(self.btn_zoom_fit)
        layout.addStretch()

        return panel

    def _create_waveform_container(self) -> QtWidgets.QWidget:
        """Tạo khung vẽ đồ thị 8 kênh tích hợp Channel Manager và Cursor HUD."""
        container = QtWidgets.QFrame()
        container.setStyleSheet("background-color: #181818; border: 1px solid #3e3e42; border-radius: 6px;")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header bar: Cursors HUD overlay
        self.hud_widget = CursorHUDWidget()
        layout.addWidget(self.hud_widget)

        # Waveform Body Splitter (Left: Channel Manager Sidebar | Right: PlotWidget)
        body_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        body_splitter.setHandleWidth(4)

        # 1. Left Channel Sidebar (Show/Hide checkboxes & Editable names)
        sidebar = QtWidgets.QFrame()
        sidebar.setStyleSheet("background-color: #202020; border-radius: 4px; padding: 2px;")
        sb_layout = QtWidgets.QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(6, 6, 6, 6)
        sb_layout.setSpacing(4)

        lbl_sb_title = QtWidgets.QLabel("<b>KÊNH LOGIC</b>")
        lbl_sb_title.setAlignment(QtCore.Qt.AlignCenter)
        lbl_sb_title.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        sb_layout.addWidget(lbl_sb_title)

        self.ch_checkboxes = []
        self.ch_name_edits = []

        for ch in range(8):
            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(4)

            # Checkbox bật/tắt
            cb = QtWidgets.QCheckBox()
            cb.setChecked(True)
            cb.setStyleSheet(f"QCheckBox::indicator:checked {{ background-color: {CHANNEL_COLORS[ch]}; border: 1px solid #fff; }}")
            cb.stateChanged.connect(lambda state, c=ch: self._on_channel_visibility_changed(c, state))
            self.ch_checkboxes.append(cb)

            # LineEdit đổi tên kênh
            edit = QtWidgets.QLineEdit(self.channel_names[ch])
            edit.setStyleSheet(f"background-color: #2b2b2b; color: {CHANNEL_COLORS[ch]}; border: 1px solid #3e3e42; border-radius: 3px; padding: 2px; font-weight: bold; font-size: 11px;")
            edit.editingFinished.connect(lambda c=ch: self._on_channel_name_changed(c))
            self.ch_name_edits.append(edit)

            row_layout.addWidget(cb)
            row_layout.addWidget(edit)
            sb_layout.addWidget(row_widget)

        sb_layout.addStretch()
        body_splitter.addWidget(sidebar)

        # 2. Right PlotWidget (pyqtgraph)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel("bottom", "Thời gian (s)", units="s")
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.setYRange(-0.5, 12.5, padding=0.02)

        self._update_plot_y_ticks()

        # Tạo 8 PlotCurveItem cho 8 kênh
        self.channel_curves = []
        for ch in range(8):
            pen = pg.mkPen(color=CHANNEL_COLORS[ch], width=1.8)
            curve = pg.PlotCurveItem(pen=pen)
            self.plot_widget.addItem(curve)
            self.channel_curves.append(curve)

        # Vạch chỉ thị Trigger màu đỏ (dọc)
        self.trigger_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(color="#ff1744", width=2, style=QtCore.Qt.DashLine),
            label="TRIGGER (t=0)",
            labelOpts={"color": "#ff1744", "position": 0.95, "anchors": [(0, 0), (0, 0)]}
        )
        self.plot_widget.addItem(self.trigger_line)
        self.trigger_line.hide()

        # Tích hợp Quản lý Cặp thước đo thời gian (Cursors A & B)
        self.cursor_manager = CursorManager(self.plot_widget, self.hud_widget)

        body_splitter.addWidget(self.plot_widget)
        body_splitter.setStretchFactor(0, 15)
        body_splitter.setStretchFactor(1, 85)

        layout.addWidget(body_splitter)
        return container

    def _update_plot_y_ticks(self):
        """Cập nhật nhãn trục Y tương ứng với tên các kênh."""
        y_ticks = []
        for ch in range(8):
            y_baseline = (7 - ch) * 1.5
            name = self.channel_names[ch]
            y_ticks.append((y_baseline + 0.5, name))
        y_axis = self.plot_widget.getAxis("left")
        y_axis.setTicks([y_ticks])
        y_axis.setWidth(110)

    def _on_channel_visibility_changed(self, ch: int, state: int):
        """Ẩn/hiện đường vẽ dạng sóng của kênh tương ứng."""
        visible = (state == QtCore.Qt.Checked)
        self.channel_visible[ch] = visible
        if ch < len(self.channel_curves):
            self.channel_curves[ch].setVisible(visible)

    def _on_channel_name_changed(self, ch: int):
        """Cập nhật tên kênh khi người dùng chỉnh sửa."""
        new_name = self.ch_name_edits[ch].text().strip()
        if new_name:
            self.channel_names[ch] = new_name
            self._update_plot_y_ticks()

    # =========================================================================
    # DECODER & PROTOCOL TERMINAL PANEL
    # =========================================================================

    def _create_decoder_panel(self) -> QtWidgets.QWidget:
        """Tạo bảng điều khiển giải mã giao thức (Tabbed: UART, I2C, SPI)."""
        tab_widget = QtWidgets.QTabWidget()

        # Tab 1: UART Decoder
        uart_tab = self._create_uart_tab()
        tab_widget.addTab(uart_tab, "⚡ UART Decoder")

        # Tab 2: I2C Decoder
        i2c_tab = self._create_i2c_tab()
        tab_widget.addTab(i2c_tab, "⚡ I2C Bus Decoder")

        # Tab 3: SPI Decoder
        spi_tab = self._create_spi_tab()
        tab_widget.addTab(spi_tab, "⚡ SPI Bus Decoder")

        return tab_widget

    def _create_uart_tab(self) -> QtWidgets.QWidget:
        """Tạo tab cấu hình & giải mã UART."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Cột trái: Cấu hình
        left_box = QtWidgets.QGroupBox("Cấu Hình UART")
        left_layout = QtWidgets.QFormLayout(left_box)
        left_layout.setContentsMargins(8, 10, 8, 8)

        self.cb_uart_ch = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_uart_ch.addItem(f"D{ch} (PA{ch})", ch)
        self.cb_uart_ch.setCurrentIndex(0)

        self.cb_uart_baud = QtWidgets.QComboBox()
        baud_list = [115200, 9600, 19200, 38400, 57600, 230400, 460800, 921600]
        for b in baud_list:
            self.cb_uart_baud.addItem(f"{b:,} bps", b)
        self.cb_uart_baud.setCurrentIndex(0)

        self.btn_decode_uart = QtWidgets.QPushButton("⚡ GIẢI MÃ UART")
        self.btn_decode_uart.setStyleSheet("background-color: #0e639c; font-weight: bold; padding: 6px;")
        self.btn_decode_uart.clicked.connect(self._on_decode_uart)

        left_layout.addRow("Kênh RX/TX:", self.cb_uart_ch)
        left_layout.addRow("Tốc Độ Baud:", self.cb_uart_baud)
        left_layout.addRow("", self.btn_decode_uart)
        layout.addWidget(left_box, 1)

        # Cột giữa: Chuỗi văn bản ASCII
        text_box = QtWidgets.QGroupBox("Chuỗi ASCII Giải Mã (Terminal)")
        text_layout = QtWidgets.QVBoxLayout(text_box)
        text_layout.setContentsMargins(8, 10, 8, 8)

        self.txt_uart_decoded = QtWidgets.QTextEdit()
        self.txt_uart_decoded.setReadOnly(True)
        self.txt_uart_decoded.setPlaceholderText("Chuỗi ASCII UART sẽ hiển thị tại đây...")
        text_layout.addWidget(self.txt_uart_decoded)
        layout.addWidget(text_box, 2)

        # Cột phải: Bảng danh sách khung ký tự
        table_box = QtWidgets.QGroupBox("Frame Inspector (Click để Zoom)")
        table_layout = QtWidgets.QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 10, 8, 8)

        self.table_uart_frames = QtWidgets.QTableWidget(0, 5)
        self.table_uart_frames.setHorizontalHeaderLabels(["#", "Thời gian", "Mẫu", "Ký tự", "Mã Hex"])
        self.table_uart_frames.horizontalHeader().setStretchLastSection(True)
        self.table_uart_frames.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_uart_frames.setAlternatingRowColors(True)
        self.table_uart_frames.cellClicked.connect(self._on_uart_frame_clicked)
        table_layout.addWidget(self.table_uart_frames)
        layout.addWidget(table_box, 3)

        return tab

    def _create_i2c_tab(self) -> QtWidgets.QWidget:
        """Tạo tab cấu hình & giải mã I2C."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Cột trái: Cấu hình
        left_box = QtWidgets.QGroupBox("Cấu Hình I2C")
        left_layout = QtWidgets.QFormLayout(left_box)
        left_layout.setContentsMargins(8, 10, 8, 8)

        self.cb_i2c_scl = QtWidgets.QComboBox()
        self.cb_i2c_sda = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_i2c_scl.addItem(f"D{ch} (PA{ch})", ch)
            self.cb_i2c_sda.addItem(f"D{ch} (PA{ch})", ch)
        self.cb_i2c_scl.setCurrentIndex(1)  # Mặc định D1 làm SCL
        self.cb_i2c_sda.setCurrentIndex(2)  # Mặc định D2 làm SDA

        self.btn_decode_i2c = QtWidgets.QPushButton("⚡ GIẢI MÃ I2C")
        self.btn_decode_i2c.setStyleSheet("background-color: #0e639c; font-weight: bold; padding: 6px;")
        self.btn_decode_i2c.clicked.connect(self._on_decode_i2c)

        left_layout.addRow("Kênh SCL:", self.cb_i2c_scl)
        left_layout.addRow("Kênh SDA:", self.cb_i2c_sda)
        left_layout.addRow("", self.btn_decode_i2c)
        layout.addWidget(left_box, 1)

        # Cột giữa: Bus Trace
        text_box = QtWidgets.QGroupBox("I2C Packet Trace")
        text_layout = QtWidgets.QVBoxLayout(text_box)
        text_layout.setContentsMargins(8, 10, 8, 8)

        self.txt_i2c_decoded = QtWidgets.QTextEdit()
        self.txt_i2c_decoded.setReadOnly(True)
        self.txt_i2c_decoded.setPlaceholderText("Luồng giao dịch I2C (START, ADDR, DATA, STOP) sẽ hiển thị tại đây...")
        text_layout.addWidget(self.txt_i2c_decoded)
        layout.addWidget(text_box, 2)

        # Cột phải: Bảng chi tiết
        table_box = QtWidgets.QGroupBox("I2C Events (Click để Zoom)")
        table_layout = QtWidgets.QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 10, 8, 8)

        self.table_i2c_frames = QtWidgets.QTableWidget(0, 5)
        self.table_i2c_frames.setHorizontalHeaderLabels(["#", "Thời gian", "Sự Kiện", "Mô Tả", "ACK/NACK"])
        self.table_i2c_frames.horizontalHeader().setStretchLastSection(True)
        self.table_i2c_frames.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_i2c_frames.setAlternatingRowColors(True)
        self.table_i2c_frames.cellClicked.connect(self._on_i2c_frame_clicked)
        table_layout.addWidget(self.table_i2c_frames)
        layout.addWidget(table_box, 3)

        return tab

    def _create_spi_tab(self) -> QtWidgets.QWidget:
        """Tạo tab cấu hình & giải mã SPI."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Cột trái: Cấu hình
        left_box = QtWidgets.QGroupBox("Cấu Hình SPI")
        left_layout = QtWidgets.QFormLayout(left_box)
        left_layout.setContentsMargins(8, 10, 8, 8)

        self.cb_spi_sck = QtWidgets.QComboBox()
        self.cb_spi_mosi = QtWidgets.QComboBox()
        self.cb_spi_miso = QtWidgets.QComboBox()
        self.cb_spi_cs = QtWidgets.QComboBox()

        self.cb_spi_cs.addItem("(Không dùng CS)", -1)
        for ch in range(8):
            self.cb_spi_sck.addItem(f"D{ch}", ch)
            self.cb_spi_mosi.addItem(f"D{ch}", ch)
            self.cb_spi_miso.addItem(f"D{ch}", ch)
            self.cb_spi_cs.addItem(f"D{ch}", ch)

        self.cb_spi_sck.setCurrentIndex(5)   # D5 làm SCK
        self.cb_spi_mosi.setCurrentIndex(3)  # D3 làm MOSI
        self.cb_spi_miso.setCurrentIndex(4)  # D4 làm MISO
        self.cb_spi_cs.setCurrentIndex(7)    # D6 làm CS (index 7 vì có option -1)

        self.cb_spi_mode = QtWidgets.QComboBox()
        self.cb_spi_mode.addItem("Mode 0 (CPOL=0, CPHA=0)", (0, 0))
        self.cb_spi_mode.addItem("Mode 1 (CPOL=0, CPHA=1)", (0, 1))
        self.cb_spi_mode.addItem("Mode 2 (CPOL=1, CPHA=0)", (1, 0))
        self.cb_spi_mode.addItem("Mode 3 (CPOL=1, CPHA=1)", (1, 1))

        self.btn_decode_spi = QtWidgets.QPushButton("⚡ GIẢI MÃ SPI")
        self.btn_decode_spi.setStyleSheet("background-color: #0e639c; font-weight: bold; padding: 6px;")
        self.btn_decode_spi.clicked.connect(self._on_decode_spi)

        left_layout.addRow("Kênh SCK:", self.cb_spi_sck)
        left_layout.addRow("Kênh MOSI:", self.cb_spi_mosi)
        left_layout.addRow("Kênh MISO:", self.cb_spi_miso)
        left_layout.addRow("Kênh CS:", self.cb_spi_cs)
        left_layout.addRow("Chế Độ:", self.cb_spi_mode)
        left_layout.addRow("", self.btn_decode_spi)
        layout.addWidget(left_box, 1)

        # Cột giữa: Data Trace
        text_box = QtWidgets.QGroupBox("SPI Byte Stream")
        text_layout = QtWidgets.QVBoxLayout(text_box)
        text_layout.setContentsMargins(8, 10, 8, 8)

        self.txt_spi_decoded = QtWidgets.QTextEdit()
        self.txt_spi_decoded.setReadOnly(True)
        self.txt_spi_decoded.setPlaceholderText("Dữ liệu song công MOSI & MISO sẽ hiển thị tại đây...")
        text_layout.addWidget(self.txt_spi_decoded)
        layout.addWidget(text_box, 2)

        # Cột phải: Bảng chi tiết
        table_box = QtWidgets.QGroupBox("SPI Bytes (Click để Zoom)")
        table_layout = QtWidgets.QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 10, 8, 8)

        self.table_spi_frames = QtWidgets.QTableWidget(0, 5)
        self.table_spi_frames.setHorizontalHeaderLabels(["#", "Thời gian", "MOSI (Hex)", "MISO (Hex)", "ASCII"])
        self.table_spi_frames.horizontalHeader().setStretchLastSection(True)
        self.table_spi_frames.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_spi_frames.setAlternatingRowColors(True)
        self.table_spi_frames.cellClicked.connect(self._on_spi_frame_clicked)
        table_layout.addWidget(self.table_spi_frames)
        layout.addWidget(table_box, 3)

        return tab

    # =========================================================================
    # STATUS BAR
    # =========================================================================

    def _init_status_bar(self):
        """Khởi tạo thanh trạng thái đáy ứng dụng."""
        status_bar = self.statusBar()
        self.lbl_sb_conn = QtWidgets.QLabel("Cổng: Chưa kết nối")
        self.lbl_sb_capture = QtWidgets.QLabel("Mẫu: 0 | Tần số: -- | Cửa sổ: --")
        self.lbl_sb_status = QtWidgets.QLabel("Trạng thái: IDLE")
        self.lbl_sb_checksum = QtWidgets.QLabel("Checksum: --")

        status_bar.addWidget(self.lbl_sb_conn, 2)
        status_bar.addWidget(self.lbl_sb_capture, 3)
        status_bar.addWidget(self.lbl_sb_status, 2)
        status_bar.addPermanentWidget(self.lbl_sb_checksum)

    # =========================================================================
    # KẾT NỐI VÀ THU THẬP DỮ LIỆU
    # =========================================================================

    def _refresh_ports(self):
        """Quét và cập nhật danh sách các cổng serial và Offline Mock."""
        self.cb_ports.clear()
        ports = self.client.list_ports()
        for dev, desc in ports:
            self.cb_ports.addItem(desc, dev)

        # Tự động chọn /dev/ttyACM0 nếu có
        for i in range(self.cb_ports.count()):
            val = self.cb_ports.itemData(i)
            if "ttyACM" in str(val) or "STM32" in str(val):
                self.cb_ports.setCurrentIndex(i)
                break

    def _on_toggle_connect(self):
        """Kết nối hoặc ngắt kết nối với cổng COM được chọn."""
        if self.client.is_connected:
            self.client.disconnect()
            self._update_connection_ui(False, "Đã ngắt kết nối")
        else:
            port = self.cb_ports.currentData()
            if not port:
                QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Không tìm thấy cổng COM nào!")
                return
            ok, msg = self.client.connect(port)
            if ok:
                ok_ping, ver = self.client.ping()
                desc = f"Đã kết nối: {port} (Firmware {ver if ok_ping else 'v1.0.0'})"
                self._update_connection_ui(True, desc)
            else:
                self._update_connection_ui(False, msg)
                QtWidgets.QMessageBox.critical(self, "Lỗi kết nối", msg)

    def _update_connection_ui(self, connected: bool, desc: str):
        """Cập nhật trạng thái nút và đèn LED kết nối."""
        if connected:
            self.btn_connect.setText("Ngắt Kết Nối")
            self.lbl_conn_status.setStyleSheet("color: #76ff03; font-size: 16px;")
            self.lbl_conn_status.setToolTip("Đang kết nối: Sẵn sàng")
            self.lbl_sb_conn.setText(f"Cổng: {desc}")
        else:
            self.btn_connect.setText("Kết Nối")
            self.lbl_conn_status.setStyleSheet("color: #ff5252; font-size: 16px;")
            self.lbl_conn_status.setToolTip("Chưa kết nối")
            self.lbl_sb_conn.setText("Cổng: Chưa kết nối")

    def _on_start_capture(self):
        """Bắt đầu chu trình thu thập dữ liệu qua luồng nền (Worker)."""
        if not self.client.is_connected:
            QtWidgets.QMessageBox.warning(self, "Chưa kết nối", "Vui lòng bấm 'Kết Nối' tới cổng COM hoặc 'Offline Mock' trước!")
            return

        rate_idx = self.cb_rate.currentData()
        trig_ch = self.cb_trig_ch.currentData()
        trig_mode = self.cb_trig_mode.currentData()

        self.btn_start.setEnabled(False)
        self.btn_abort.setEnabled(True)
        self.lbl_sb_status.setText("Trạng thái: Đang thu thập dữ liệu...")

        self.capture_worker = CaptureWorker(self.client, rate_idx, trig_ch, trig_mode)
        self.capture_worker.capture_done.connect(self._on_capture_finished)
        self.capture_worker.capture_error.connect(self._on_capture_failed)
        self.capture_worker.start()

    def _on_abort(self):
        """Gửi lệnh khẩn cấp ABORT dừng chu trình lấy mẫu."""
        ok, msg = self.client.abort()
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self.lbl_sb_status.setText(f"Trạng thái: {msg}")

    def _on_capture_finished(self, res: Dict[str, Any]):
        """Callback khi thu thập 32.776B hoàn tất thành công."""
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self._render_capture_data(res)

    def _on_capture_failed(self, err_msg: str):
        """Callback khi xảy ra lỗi trong quá trình thu thập."""
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self.lbl_sb_status.setText(f"Lỗi: {err_msg}")
        QtWidgets.QMessageBox.warning(self, "Thu thập thất bại", err_msg)

    def _on_browse_bin(self):
        """Mở tệp nhị phân .bin offline từ ổ cứng."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Chọn Tệp Dữ Liệu Logic Analyzer", "", "Binary Data (*.bin);;All Files (*)"
        )
        if filepath:
            self._load_bin_file(filepath)

    def _load_bin_file(self, filepath: str):
        """Nạp dữ liệu từ tệp binary offline."""
        res = self.client.load_offline_file(filepath)
        if res.get("success", False):
            self._render_capture_data(res)
            self.lbl_sb_conn.setText(f"Nguồn: Tệp offline ({os.path.basename(filepath)})")
        else:
            QtWidgets.QMessageBox.critical(self, "Lỗi đọc tệp", res.get("error", "Lỗi không xác định"))

    # =========================================================================
    # HIỂN THỊ ĐỒ THỊ VÀ VẼ SÓNG
    # =========================================================================

    def _render_capture_data(self, res: Dict[str, Any]):
        """Vẽ dạng sóng 8 kênh và đồng bộ mốc thời gian quanh Trigger."""
        self.current_data = res
        channels = res["channels"]
        sample_rate = res["sample_rate"]
        sample_count = res["sample_count"]
        trig_offset = res["trig_offset"]
        status = res.get("status", 0)
        elapsed_s = res.get("elapsed_s", 0.0)

        # Cập nhật tần số cho các bộ giải mã
        self.uart_decoder.sample_rate = sample_rate
        self.i2c_decoder.sample_rate = sample_rate
        self.spi_decoder.sample_rate = sample_rate

        # Căn chỉnh trục thời gian t=0 ngay tại Trigger nếu bắt cạnh thành công
        if status == 0:  # STATUS_TRIGGER_OK
            time_axis = (np.arange(sample_count + 1, dtype=np.float64) - trig_offset) / sample_rate
            trigger_pos = 0.0
            self.trigger_line.setValue(trigger_pos)
            self.trigger_line.setPen(pg.mkPen(color="#ff1744", width=2, style=QtCore.Qt.DashLine))
            self.trigger_line.label.setText("TRIGGER (t=0)")
            self.trigger_line.show()
            x_min = -trig_offset / sample_rate
            x_max = (sample_count - trig_offset) / sample_rate
        elif status == 1:  # STATUS_FREERUN_OK
            time_axis = np.arange(sample_count + 1, dtype=np.float64) / sample_rate
            trigger_pos = trig_offset / sample_rate
            self.trigger_line.setValue(trigger_pos)
            self.trigger_line.setPen(pg.mkPen(color="#888888", width=1.5, style=QtCore.Qt.DotLine))
            self.trigger_line.label.setText("MỐC 20% (FREE-RUN)")
            self.trigger_line.show()
            x_min = 0.0
            x_max = sample_count / sample_rate
        else:  # STATUS_TIMEOUT
            time_axis = np.arange(sample_count + 1, dtype=np.float64) / sample_rate
            trigger_pos = trig_offset / sample_rate
            self.trigger_line.setValue(trigger_pos)
            self.trigger_line.setPen(pg.mkPen(color="#ff9100", width=1.8, style=QtCore.Qt.DashDotLine))
            self.trigger_line.label.setText("TIMEOUT")
            self.trigger_line.show()
            x_min = 0.0
            x_max = sample_count / sample_rate

        # Vẽ từng kênh trên đồ thị
        for ch in range(8):
            ch_data = channels[ch].astype(np.float32)
            y_base = (7 - ch) * 1.5
            y_data = ch_data + y_base
            self.channel_curves[ch].setData(x=time_axis, y=y_data, stepMode="center")
            self.channel_curves[ch].setVisible(self.channel_visible[ch])

        # Đặt vị trí ban đầu cho Thước đo Cursors
        t_a_init = trigger_pos
        t_b_init = trigger_pos + (86.8e-6 if status == 0 else 0.001)
        self.cursor_manager.set_positions(t_a_init, t_b_init)

        # Zoom vừa vặn
        self.plot_widget.setXRange(x_min, x_max, padding=0.01)

        # Cập nhật thanh trạng thái
        dur_ms = (sample_count / sample_rate) * 1000.0
        self.lbl_sb_capture.setText(
            f"Mẫu: {sample_count:,} | Tần số: {sample_rate/1e6:.2f} MHz | Cửa sổ: {dur_ms:.2f} ms"
        )
        self.lbl_sb_status.setText(f"Trạng thái: {res['status_name']} (Truyền: {elapsed_s:.3f} s)")
        csum_byte = res.get("payload")[0] if len(res.get("payload", [])) else 0
        self.lbl_sb_checksum.setText(f"Checksum XOR: {'PASS (0x%02X)' % csum_byte if res['checksum_ok'] else 'FAIL'}")

        # Tự động giải mã UART mặc định
        self._on_decode_uart()

    def _zoom_fit(self):
        """Khôi phục tầm nhìn toàn cảnh đồ thị."""
        if self.current_data:
            sample_count = self.current_data["sample_count"]
            sample_rate = self.current_data["sample_rate"]
            trig_offset = self.current_data["trig_offset"]
            status = self.current_data.get("status", 0)

            if status == 0:
                x_min = -trig_offset / sample_rate
                x_max = (sample_count - trig_offset) / sample_rate
            else:
                x_min = 0.0
                x_max = sample_count / sample_rate
            self.plot_widget.setXRange(x_min, x_max, padding=0.01)

    def _toggle_cursors(self):
        """Bật/tắt cặp thước đo thời gian A/B."""
        is_vis = self.cursor_manager.is_visible()
        self.cursor_manager.set_visible(not is_vis)

    # =========================================================================
    # THỰC THI GIẢI MÃ GIAO THỨC (DECODERS)
    # =========================================================================

    def _on_decode_uart(self):
        """Giải mã UART từ kênh được chọn."""
        if not self.current_data:
            return

        ch_idx = self.cb_uart_ch.currentData()
        baudrate = self.cb_uart_baud.currentData()
        sample_rate = self.current_data["sample_rate"]
        ch_arr = self.current_data["channels"][ch_idx]
        samples = ch_arr.tolist()

        self.uart_decoder.sample_rate = sample_rate
        self.uart_decoder.baudrate = baudrate

        decoded_text, frames = self.uart_decoder.decode(samples, start_idx=0)
        self.current_uart_frames = frames

        if decoded_text:
            self.txt_uart_decoded.setStyleSheet("color: #00e5ff; font-size: 14px; font-weight: bold;")
            self.txt_uart_decoded.setPlainText(decoded_text)
        else:
            num_ones = int(np.count_nonzero(ch_arr == 1))
            num_zeros = len(ch_arr) - num_ones
            transitions = int(np.count_nonzero(np.diff(ch_arr) != 0))

            self.txt_uart_decoded.setStyleSheet("color: #ffb74d; font-size: 13px; font-family: monospace;")
            if transitions == 0 and num_ones == 0:
                diag = (
                    f"⚠️ KÊNH D{ch_idx} (PA{ch_idx}) ĐANG Ở MỨC LOW (0V) LIÊN TỤC (0 LẦN CHUYỂN MỨC)\n\n"
                    f"• Nguyên nhân: Chân PA{ch_idx} đang thả nổi với trở kéo xuống nội (Pull-down).\n"
                    f"• Khắc phục: Cắm 1 sợi dây Jumper từ chân PA9 (USART1_TX test) sang chân PA0 (D0) rồi bấm Start Capture lại!"
                )
            elif transitions == 0 and num_zeros == 0:
                diag = f"⚠️ KÊNH D{ch_idx} ĐANG Ở MỨC HIGH LIÊN TỤC (TÍN HIỆU NGHỈ IDLE)\n• Không có ký tự nào được phát trong khung thời gian đo."
            else:
                diag = f"⚠️ PHÁT HIỆN {transitions:,} LẦN CHUYỂN MỨC NHƯNG KHÔNG GIẢI MÃ ĐƯỢC UART\n• Hãy kiểm tra Tốc độ Baud ({baudrate:,} bps) hoặc Kênh giải mã."
            self.txt_uart_decoded.setPlainText(diag)

        # Cập nhật bảng
        self.table_uart_frames.setRowCount(len(frames))
        for row, f in enumerate(frames):
            time_ms = f["start_time_s"] * 1000.0
            self.table_uart_frames.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))
            self.table_uart_frames.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{time_ms:.3f} ms"))
            self.table_uart_frames.setItem(row, 2, QtWidgets.QTableWidgetItem(str(f["start_sample"])))
            char_disp = repr(f["char"])[1:-1]
            self.table_uart_frames.setItem(row, 3, QtWidgets.QTableWidgetItem(char_disp))
            self.table_uart_frames.setItem(row, 4, QtWidgets.QTableWidgetItem(f"0x{f['byte_val']:02X}"))

    def _on_uart_frame_clicked(self, row: int, col: int):
        """Phóng to căn giữa ký tự UART được nhấp trong bảng."""
        if hasattr(self, "current_uart_frames") and 0 <= row < len(self.current_uart_frames):
            f = self.current_uart_frames[row]
            self._zoom_to_time_window(f["start_time_s"], f["stop_time_s"])

    def _on_decode_i2c(self):
        """Giải mã I2C từ 2 kênh SCL và SDA."""
        if not self.current_data:
            return

        scl_ch = self.cb_i2c_scl.currentData()
        sda_ch = self.cb_i2c_sda.currentData()
        scl_samples = self.current_data["channels"][scl_ch].tolist()
        sda_samples = self.current_data["channels"][sda_ch].tolist()

        decoded_text, frames = self.i2c_decoder.decode(scl_samples, sda_samples)
        self.current_i2c_frames = frames

        self.txt_i2c_decoded.setPlainText(decoded_text if decoded_text else "[Không phát hiện giao dịch I2C hợp lệ trên 2 kênh này]")

        self.table_i2c_frames.setRowCount(len(frames))
        for row, f in enumerate(frames):
            time_ms = f["start_time_s"] * 1000.0
            self.table_i2c_frames.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))
            self.table_i2c_frames.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{time_ms:.3f} ms"))
            self.table_i2c_frames.setItem(row, 2, QtWidgets.QTableWidgetItem(f["type"]))
            self.table_i2c_frames.setItem(row, 3, QtWidgets.QTableWidgetItem(f["desc"]))
            ack_str = "ACK" if f.get("ack") else ("NACK" if f.get("type") in ("ADDRESS", "DATA") else "--")
            self.table_i2c_frames.setItem(row, 4, QtWidgets.QTableWidgetItem(ack_str))

    def _on_i2c_frame_clicked(self, row: int, col: int):
        """Phóng to căn giữa sự kiện I2C được nhấp trong bảng."""
        if hasattr(self, "current_i2c_frames") and 0 <= row < len(self.current_i2c_frames):
            f = self.current_i2c_frames[row]
            self._zoom_to_time_window(f["start_time_s"], f["stop_time_s"])

    def _on_decode_spi(self):
        """Giải mã SPI từ 4 kênh SCK, MOSI, MISO, CS."""
        if not self.current_data:
            return

        sck_ch = self.cb_spi_sck.currentData()
        mosi_ch = self.cb_spi_mosi.currentData()
        miso_ch = self.cb_spi_miso.currentData()
        cs_ch = self.cb_spi_cs.currentData()
        cpol, cpha = self.cb_spi_mode.currentData()

        sck_samples = self.current_data["channels"][sck_ch].tolist()
        mosi_samples = self.current_data["channels"][mosi_ch].tolist()
        miso_samples = self.current_data["channels"][miso_ch].tolist()
        cs_samples = self.current_data["channels"][cs_ch].tolist() if cs_ch >= 0 else None

        self.spi_decoder.cpol = cpol
        self.spi_decoder.cpha = cpha

        decoded_text, frames = self.spi_decoder.decode(sck_samples, mosi_samples, miso_samples, cs_samples)
        self.current_spi_frames = frames

        self.txt_spi_decoded.setPlainText(decoded_text if decoded_text else "[Không phát hiện frame SPI hợp lệ]")

        self.table_spi_frames.setRowCount(len(frames))
        for row, f in enumerate(frames):
            time_ms = f["start_time_s"] * 1000.0
            self.table_spi_frames.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))
            self.table_spi_frames.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{time_ms:.3f} ms"))
            self.table_spi_frames.setItem(row, 2, QtWidgets.QTableWidgetItem(f["mosi_hex"]))
            self.table_spi_frames.setItem(row, 3, QtWidgets.QTableWidgetItem(f["miso_hex"]))
            self.table_spi_frames.setItem(row, 4, QtWidgets.QTableWidgetItem(f"'{f['mosi_ascii']}' / '{f['miso_ascii']}'"))

    def _on_spi_frame_clicked(self, row: int, col: int):
        """Phóng to căn giữa byte SPI được nhấp trong bảng."""
        if hasattr(self, "current_spi_frames") and 0 <= row < len(self.current_spi_frames):
            f = self.current_spi_frames[row]
            self._zoom_to_time_window(f["start_time_s"], f["stop_time_s"])

    def _zoom_to_time_window(self, t_start_abs: float, t_stop_abs: float):
        """Phóng to tầm nhìn vào một khoảng thời gian cụ thể."""
        if not self.current_data:
            return

        status = self.current_data.get("status", 0)
        sample_rate = self.current_data["sample_rate"]
        trig_offset = self.current_data["trig_offset"]

        # Nếu đang ở chế độ Trigger và trục hoành căn t=0 tại trigger:
        if status == 0:
            offset_s = trig_offset / sample_rate
            t1 = t_start_abs - offset_s
            t2 = t_stop_abs - offset_s
        else:
            t1 = t_start_abs
            t2 = t_stop_abs

        dur = max(t2 - t1, 0.00005)
        self.plot_widget.setXRange(t1 - dur * 0.4, t2 + dur * 0.4, padding=0)

    # =========================================================================
    # XUẤT DỮ LIỆU ĐA ĐỊNH DẠNG (EXPORT)
    # =========================================================================

    def _on_export_image(self):
        """Xuất ảnh đồ thị PNG hoặc SVG."""
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Xuất Ảnh Dạng Sóng", "waveform_capture.png", "PNG Image (*.png);;SVG Image (*.svg)"
        )
        if filepath:
            if export_image(self.plot_widget, filepath):
                QtWidgets.QMessageBox.information(self, "Thành Công", f"Đã xuất hình ảnh thành công:\n{filepath}")
            else:
                QtWidgets.QMessageBox.critical(self, "Thất Bại", "Lỗi khi xuất hình ảnh!")

    def _on_export_csv(self):
        """Xuất dữ liệu 8 kênh ra bảng tính CSV."""
        if not self.current_data:
            QtWidgets.QMessageBox.warning(self, "Chưa có dữ liệu", "Vui lòng thu thập dữ liệu trước khi xuất CSV!")
            return

        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Xuất Tệp Bảng Tính CSV", "logic_data.csv", "CSV Files (*.csv)"
        )
        if filepath:
            if export_csv(self.current_data, filepath):
                QtWidgets.QMessageBox.information(self, "Thành Công", f"Đã xuất 32.768 mẫu ra tệp CSV:\n{filepath}")
            else:
                QtWidgets.QMessageBox.critical(self, "Thất Bại", "Lỗi khi ghi tệp CSV!")

    def _on_export_vcd(self):
        """Xuất dữ liệu xung số ra file chuẩn GTKWave VCD."""
        if not self.current_data:
            QtWidgets.QMessageBox.warning(self, "Chưa có dữ liệu", "Vui lòng thu thập dữ liệu trước khi xuất VCD!")
            return

        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Xuất Tệp VCD (GTKWave)", "waveform.vcd", "Value Change Dump (*.vcd)"
        )
        if filepath:
            if export_vcd(self.current_data, filepath):
                QtWidgets.QMessageBox.information(self, "Thành Công", f"Đã xuất tệp VCD chuẩn GTKWave:\n{filepath}")
            else:
                QtWidgets.QMessageBox.critical(self, "Thất Bại", "Lỗi khi ghi tệp VCD!")

    def _show_about_dialog(self):
        """Hiển thị hộp thoại giới thiệu đề tài."""
        about_text = (
            "<h2>HUST STM32 Logic Analyzer 8-Channel 6MHz</h2>"
            "<p><b>Lead Developer:</b> Nguyễn Văn Hội</p>"
            "<p><b>Phần Cứng:</b> STM32F401CCU6 WeAct Black Pill V3.0 (ARM Cortex-M4 @ 84 MHz)</p>"
            "<p><b>Kiến Trúc Firmware:</b> TIM1 Update -> DMA2_Stream5 Circular -> TIM2 Cascade Post-trigger -> USB OTG_FS CDC</p>"
            "<p><b>Giao Thức:</b> Nhị phân chuẩn SSoT <code>protocol.md</code> (Data Frame 32.776 Bytes, XOR Checksum)</p>"
            "<p><b>Phần Mềm Desktop:</b> Python 3, PyQt5, pyqtgraph, Decoders (UART, I2C, SPI), Cursors A/B, VCD/CSV/PNG Exporter.</p>"
        )
        QtWidgets.QMessageBox.about(self, "Giới Thiệu Đề Tài", about_text)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
