#!/usr/bin/env python3
"""
software/gui/main_window.py
Giao diện người dùng Desktop (PyQt5 + pyqtgraph) cho STM32 Logic Analyzer.
Thiết kế Dark Mode chuyên nghiệp (phong cách Saleae Logic / DSView).

Chức năng:
1. Control Panel: Kết nối cổng serial, chọn tần số (10 kHz - 6 MHz), cấu hình Trigger (CH0-CH7, Free-run/Edge), Start/Abort capture.
2. Waveform Viewer: Hiển thị 8 kênh số xếp tầng mượt mà 60 FPS, vạch đỏ chỉ thị Trigger tại mẫu 6554, Zoom/Pan tự do.
3. Protocol Decoder Panel: Giải mã UART thời gian thực từ kênh chỉ định, hiển thị chuỗi ký tự ASCII và bảng khung bit chi tiết.
4. Offline Test Mode: Nạp trực tiếp tệp .bin giả lập mà không cần phần cứng.
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


# 8 màu sắc tương phản cao cho 8 kênh logic (D0 đến D7)
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

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #3e3e42;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    font-weight: bold;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
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
    font-size: 14px;
    padding: 8px 16px;
}
QPushButton#btn_start:hover {
    background-color: #138749;
}
QPushButton#btn_abort {
    background-color: #a80000;
    border-color: #a80000;
    font-weight: bold;
    font-size: 14px;
    padding: 8px 16px;
}
QPushButton#btn_abort:hover {
    background-color: #c40000;
}
QComboBox {
    background-color: #252526;
    color: #ffffff;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 5px 8px;
    min-height: 20px;
}
QComboBox:hover {
    border-color: #007acc;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #252526;
    color: #ffffff;
    selection-background-color: #0e639c;
    border: 1px solid #3e3e42;
}
QTextEdit, QTableWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
}
QHeaderView::section {
    background-color: #2d2d30;
    color: #cccccc;
    padding: 4px;
    border: 1px solid #3e3e42;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #3e3e42;
    border-radius: 4px;
    text-align: center;
    background-color: #252526;
    color: #ffffff;
    height: 16px;
}
QProgressBar::chunk {
    background-color: #007acc;
    border-radius: 3px;
}
QSplitter::handle {
    background-color: #3e3e42;
}
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
    font-weight: 500;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #1e1e1e;
    border: none;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #3e3e42;
    border-radius: 4px;
}
QScrollBar::handle:hover {
    background-color: #505054;
}
"""


class CaptureWorker(QtCore.QThread):
    """Worker Thread thực thi thu thập dữ liệu serial trong nền để không làm đơ GUI."""
    finished = QtCore.pyqtSignal(dict)
    progress = QtCore.pyqtSignal(int, int)
    error = QtCore.pyqtSignal(str)

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
                trig_mode=self.trig_mode,
                progress_callback=self.on_progress
            )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

    def on_progress(self, current: int, total: int):
        self.progress.emit(current, total)


class MainWindow(QtWidgets.QMainWindow):
    """Cửa sổ chính của ứng dụng Logic Analyzer Desktop."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 Logic Analyzer (8 Channels / 6 MHz) — Topic 1")
        self.resize(1360, 850)
        self.setStyleSheet(DARK_STYLESHEET)

        # Khởi tạo client & decoder
        self.client = LogicAnalyzerClient()
        self.decoder = UARTDecoder()
        self.capture_worker: Optional[CaptureWorker] = None

        # Dữ liệu thu thập hiện tại
        self.current_data: Optional[Dict[str, Any]] = None
        self.channel_curves: List[pg.PlotCurveItem] = []
        self.channel_shadows: List[pg.PlotCurveItem] = []
        self.trigger_line: Optional[pg.InfiniteLine] = None

        self._init_ui()
        self._refresh_ports()

        # Tự động nạp file test mẫu ban đầu để hiển thị waveform mẫu ngay khi mở app
        default_sample = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tests", "sample_data_1mhz.bin"
        )
        if os.path.exists(default_sample):
            self._load_bin_file(default_sample)

        # Hỗ trợ tự động thoát khi kiểm thử CI/CD không có người dùng tương tác
        if os.environ.get("LA_AUTO_QUIT") == "1":
            QtCore.QTimer.singleShot(600, self.close)

    def _init_ui(self):
        """Khởi tạo toàn bộ các thành phần giao diện."""
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # 1. Top Control Bar (Cấu hình cổng & lấy mẫu)
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel)

        # 2. Main Content Splitter (Waveform Viewer trên + Decoder Panel dưới)
        content_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        content_splitter.setHandleWidth(6)

        # Waveform Viewer
        waveform_container = self._create_waveform_viewer()
        content_splitter.addWidget(waveform_container)

        # Decoder & Analysis Panel
        decoder_panel = self._create_decoder_panel()
        content_splitter.addWidget(decoder_panel)

        # Phân chia tỷ lệ chiều cao: 65% cho Waveform, 35% cho Decoder
        content_splitter.setStretchFactor(0, 65)
        content_splitter.setStretchFactor(1, 35)

        main_layout.addWidget(content_splitter)

        # 3. Status Bar
        self._init_status_bar()

    def _create_control_panel(self) -> QtWidgets.QWidget:
        """Tạo thanh công cụ điều khiển trên đỉnh giao diện."""
        panel = QtWidgets.QFrame()
        panel.setStyleSheet("background-color: #252526; border-radius: 6px; padding: 4px;")
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        # Group 1: Kết nối COM / USB
        lbl_conn = QtWidgets.QLabel("<b>Cổng COM / USB:</b>")
        self.cb_ports = QtWidgets.QComboBox()
        self.cb_ports.setMinimumWidth(160)

        self.btn_refresh = QtWidgets.QPushButton("↻")
        self.btn_refresh.setToolTip("Quét lại danh sách cổng serial")
        self.btn_refresh.clicked.connect(self._refresh_ports)

        self.btn_connect = QtWidgets.QPushButton("Kết Nối")
        self.btn_connect.clicked.connect(self._toggle_connection)

        self.lbl_status_led = QtWidgets.QLabel("● Chưa kết nối")
        self.lbl_status_led.setStyleSheet("color: #ff5252; font-weight: bold;")

        self.btn_ping = QtWidgets.QPushButton("Ping")
        self.btn_ping.setToolTip("Kiểm tra kết nối và phiên bản Firmware")
        self.btn_ping.clicked.connect(self._on_ping)

        layout.addWidget(lbl_conn)
        layout.addWidget(self.cb_ports)
        layout.addWidget(self.btn_refresh)
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.lbl_status_led)
        layout.addWidget(self.btn_ping)

        # Đường phân cách
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.VLine)
        sep1.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep1)

        # Group 2: Tham số lấy mẫu
        lbl_rate = QtWidgets.QLabel("<b>Tần số:</b>")
        self.cb_rate = QtWidgets.QComboBox()
        for item in self.client.RATE_TABLE:
            self.cb_rate.addItem(item["label"], item["idx"])
        self.cb_rate.setCurrentIndex(3)  # Mặc định 1 MHz (ARR=83)

        lbl_trig_ch = QtWidgets.QLabel("<b>Kênh Trigger:</b>")
        self.cb_trig_ch = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_trig_ch.addItem(f"CH{ch} (PA{ch})", ch)
        self.cb_trig_ch.setCurrentIndex(0)  # Mặc định CH0 (PA0)

        lbl_trig_mode = QtWidgets.QLabel("<b>Kiểu Trigger:</b>")
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

        # Group 3: Nút hành động chính
        self.btn_start = QtWidgets.QPushButton("▶ START CAPTURE")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self._on_start_capture)

        self.btn_abort = QtWidgets.QPushButton("⏹ ABORT")
        self.btn_abort.setObjectName("btn_abort")
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self._on_abort)

        self.btn_load_bin = QtWidgets.QPushButton("📂 Nạp File .BIN")
        self.btn_load_bin.setToolTip("Mở tệp nhị phân offline (32.776 Bytes) để kiểm tra không cần mạch")
        self.btn_load_bin.clicked.connect(self._on_browse_bin)

        self.btn_zoom_fit = QtWidgets.QPushButton("🔍 Zoom Fit")
        self.btn_zoom_fit.setToolTip("Phóng to thu nhỏ vừa vặn toàn bộ 32.768 mẫu")
        self.btn_zoom_fit.clicked.connect(self._zoom_fit)

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_abort)
        layout.addWidget(self.btn_load_bin)
        layout.addWidget(self.btn_zoom_fit)
        layout.addStretch()

        return panel

    def _create_waveform_viewer(self) -> QtWidgets.QWidget:
        """Tạo khu vực đồ thị pyqtgraph hiển thị 8 kênh tín hiệu logic."""
        container = QtWidgets.QFrame()
        container.setStyleSheet("background-color: #1e1e1e; border: 1px solid #3e3e42; border-radius: 6px;")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        # Cấu hình pyqtgraph tối ưu Dark Theme
        pg.setConfigOption("background", "#1e1e1e")
        pg.setConfigOption("foreground", "#cccccc")
        pg.setConfigOption("antialias", False)  # Tắt antialias để đạt 60 FPS mượt mà cho 32KB điểm

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel("bottom", "Thời gian (Time)", units="s")

        # Khóa trục Y (chỉ cho phép Zoom & Pan theo trục thời gian X)
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.setYRange(-0.5, 12.5, padding=0.02)

        # Cài đặt nhãn kênh bên trái trục Y: D0 ở đỉnh, D7 ở đáy
        y_ticks = []
        for ch in range(8):
            y_baseline = (7 - ch) * 1.5
            y_ticks.append((y_baseline + 0.5, f"D{ch} (PA{ch})"))
        y_axis = self.plot_widget.getAxis("left")
        y_axis.setTicks([y_ticks])
        y_axis.setWidth(100)

        # Tạo sẵn 8 PlotCurveItem cho 8 kênh
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

        layout.addWidget(self.plot_widget)
        return container

    def _create_decoder_panel(self) -> QtWidgets.QWidget:
        """Tạo bảng điều khiển giải mã giao thức (Protocol Decoder) bên dưới."""
        container = QtWidgets.QFrame()
        container.setStyleSheet("background-color: #252526; border: 1px solid #3e3e42; border-radius: 6px;")
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # Cột trái: Tùy chọn giải mã
        left_box = QtWidgets.QGroupBox("Cấu Hình Giải Mã Giao Thức (UART)")
        left_layout = QtWidgets.QFormLayout(left_box)
        left_layout.setContentsMargins(8, 12, 8, 8)
        left_layout.setSpacing(8)

        self.cb_decode_ch = QtWidgets.QComboBox()
        for ch in range(8):
            self.cb_decode_ch.addItem(f"Kênh D{ch} (PA{ch})", ch)
        self.cb_decode_ch.setCurrentIndex(0)  # Mặc định CH0

        self.cb_decode_baud = QtWidgets.QComboBox()
        baud_list = [115200, 9600, 19200, 38400, 57600, 230400, 460800, 921600]
        for b in baud_list:
            self.cb_decode_baud.addItem(f"{b:,} bps", b)
        self.cb_decode_baud.setCurrentIndex(0)  # Mặc định 115200

        self.btn_decode = QtWidgets.QPushButton("⚡ GIẢI MÃ UART")
        self.btn_decode.setStyleSheet("background-color: #0e639c; font-weight: bold; padding: 6px;")
        self.btn_decode.clicked.connect(self._on_decode_uart)

        left_layout.addRow("Kênh Dữ Liệu:", self.cb_decode_ch)
        left_layout.addRow("Tốc Độ Baud:", self.cb_decode_baud)
        left_layout.addRow("", self.btn_decode)

        layout.addWidget(left_box, 1)

        # Cột giữa: Chuỗi văn bản ASCII đã giải mã
        text_box = QtWidgets.QGroupBox("Chuỗi Ký Tự Giải Mã (ASCII Output)")
        text_layout = QtWidgets.QVBoxLayout(text_box)
        text_layout.setContentsMargins(8, 12, 8, 8)

        self.txt_decoded = QtWidgets.QTextEdit()
        self.txt_decoded.setReadOnly(True)
        self.txt_decoded.setStyleSheet("color: #00e5ff; font-size: 14px; font-weight: bold;")
        self.txt_decoded.setPlaceholderText("Chuỗi ASCII sẽ hiển thị tại đây sau khi giải mã...")
        text_layout.addWidget(self.txt_decoded)

        layout.addWidget(text_box, 2)

        # Cột phải: Bảng chi tiết từng byte / frame
        table_box = QtWidgets.QGroupBox("Danh Sách Khung Ký Tự (Frame Inspector)")
        table_layout = QtWidgets.QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 12, 8, 8)

        self.table_frames = QtWidgets.QTableWidget(0, 5)
        self.table_frames.setHorizontalHeaderLabels(["#", "Thời gian (ms)", "Mẫu", "Ký tự", "Mã Hex"])
        self.table_frames.horizontalHeader().setStretchLastSection(True)
        self.table_frames.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_frames.setAlternatingRowColors(True)
        self.table_frames.cellClicked.connect(self._on_frame_clicked)
        table_layout.addWidget(self.table_frames)

        layout.addWidget(table_box, 3)

        return container

    def _init_status_bar(self):
        """Khởi tạo thanh trạng thái phía đáy ứng dụng."""
        status_bar = self.statusBar()

        self.lbl_sb_conn = QtWidgets.QLabel("Thiết bị: Chưa kết nối")
        self.lbl_sb_capture = QtWidgets.QLabel("Mẫu: 0 | Tần số: 1 MHz | Cửa sổ: 0 ms")
        self.lbl_sb_status = QtWidgets.QLabel("Trạng thái: Sẵn sàng")
        self.lbl_sb_checksum = QtWidgets.QLabel("Checksum: N/A")

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximumWidth(180)
        self.progress_bar.setVisible(False)

        status_bar.addWidget(self.lbl_sb_conn, 2)
        status_bar.addWidget(self.lbl_sb_capture, 3)
        status_bar.addWidget(self.lbl_sb_status, 3)
        status_bar.addWidget(self.lbl_sb_checksum, 2)
        status_bar.addPermanentWidget(self.progress_bar)

    # =========================================================================
    # CÁC HÀM XỬ LÝ SỰ KIỆN KẾT NỐI & ĐIỀU KHIỂN
    # =========================================================================

    def _refresh_ports(self):
        """Quét và làm mới danh sách cổng serial."""
        self.cb_ports.clear()
        ports = self.client.list_ports()
        default_index = 0
        for i, (p_dev, p_desc) in enumerate(ports):
            self.cb_ports.addItem(p_desc, p_dev)
            # Ưu tiên chọn cổng ttyACM0 (của STM32 Black Pill trên Linux)
            if "ttyACM" in p_dev or "STM" in p_desc:
                default_index = i

        if ports:
            self.cb_ports.setCurrentIndex(default_index)
            self.btn_connect.setEnabled(True)
        else:
            self.cb_ports.addItem("Không tìm thấy cổng COM", "")
            self.btn_connect.setEnabled(False)

    def _toggle_connection(self):
        """Kết nối hoặc ngắt kết nối cổng serial."""
        if self.client.is_connected:
            self.client.disconnect()
            self.btn_connect.setText("Kết Nối")
            self.lbl_status_led.setText("● Đã ngắt kết nối")
            self.lbl_status_led.setStyleSheet("color: #ff5252; font-weight: bold;")
            self.lbl_sb_conn.setText("Thiết bị: Đã ngắt kết nối")
        else:
            port = self.cb_ports.currentData()
            if not port:
                QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn cổng serial hợp lệ!")
                return

            ok, msg = self.client.connect(port)
            if ok:
                self.btn_connect.setText("Ngắt Kết Nối")
                self.lbl_status_led.setText("● Đang kết nối")
                self.lbl_status_led.setStyleSheet("color: #00e676; font-weight: bold;")
                self.lbl_sb_conn.setText(f"Thiết bị: {port}")
                # Tự động gửi lệnh PING để kiểm tra phiên bản Firmware
                self._on_ping(silent=True)
            else:
                QtWidgets.QMessageBox.critical(self, "Lỗi kết nối", msg)

    def _on_ping(self, silent: bool = False):
        """Gửi lệnh PING kiểm tra kết nối với MCU."""
        if not self.client.is_connected:
            if not silent:
                QtWidgets.QMessageBox.warning(self, "Thông báo", "Vui lòng kết nối cổng COM trước khi PING!")
            return

        ok, ver = self.client.ping()
        if ok:
            self.lbl_status_led.setText(f"● STM32 Online ({ver})")
            self.lbl_status_led.setStyleSheet("color: #00e676; font-weight: bold;")
            self.lbl_sb_conn.setText(f"Thiết bị: {self.client.port_name} ({ver})")
            if not silent:
                QtWidgets.QMessageBox.information(
                    self, "Kết quả PING",
                    f"Phản hồi PONG hợp lệ từ STM32!\nPhiên bản Firmware: {ver}"
                )
        else:
            self.lbl_status_led.setText("● Lỗi PING")
            self.lbl_status_led.setStyleSheet("color: #ffd600; font-weight: bold;")
            if not silent:
                QtWidgets.QMessageBox.warning(self, "PING thất bại", ver)

    def _on_start_capture(self):
        """Bắt đầu chu trình thu thập tín hiệu logic từ MCU."""
        if not self.client.is_connected:
            QtWidgets.QMessageBox.warning(
                self, "Chưa kết nối",
                "Chưa kết nối phần cứng thật!\nBạn có thể bấm nút 'Nạp File .BIN' để kiểm thử ngay lập tức."
            )
            return

        rate_idx = self.cb_rate.currentData()
        trig_ch = self.cb_trig_ch.currentData()
        trig_mode = self.cb_trig_mode.currentData()

        # Khóa giao diện để tránh gửi lệnh đè
        self.btn_start.setEnabled(False)
        self.btn_abort.setEnabled(True)
        self.btn_connect.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.lbl_sb_status.setText("Trạng thái: Đang thu thập dữ liệu...")

        # Khởi chạy worker thread
        self.capture_worker = CaptureWorker(self.client, rate_idx, trig_ch, trig_mode)
        self.capture_worker.progress.connect(self._on_capture_progress)
        self.capture_worker.finished.connect(self._on_capture_finished)
        self.capture_worker.error.connect(self._on_capture_error)
        self.capture_worker.start()

    def _on_capture_progress(self, current: int, total: int):
        """Cập nhật tiến trình nhận byte qua USB-CDC."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

    def _on_capture_finished(self, res: Dict[str, Any]):
        """Xử lý gói dữ liệu hoàn chỉnh sau khi nhận từ MCU."""
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self.btn_connect.setEnabled(True)
        self.progress_bar.setVisible(False)

        if not res.get("success", False):
            QtWidgets.QMessageBox.warning(self, "Lỗi Thu Thập", res.get("error", "Lỗi không xác định"))
            self.lbl_sb_status.setText(f"Lỗi: {res.get('error')}")
            return

        self._render_capture_data(res)

    def _on_capture_error(self, err_msg: str):
        """Bắt lỗi ngoại lệ từ worker thread."""
        self.btn_start.setEnabled(True)
        self.btn_abort.setEnabled(False)
        self.btn_connect.setEnabled(True)
        self.progress_bar.setVisible(False)
        QtWidgets.QMessageBox.critical(self, "Lỗi nghiêm trọng", f"Ngoại lệ khi thu thập dữ liệu: {err_msg}")
        self.lbl_sb_status.setText(f"Lỗi: {err_msg}")

    def _on_abort(self):
        """Gửi lệnh dừng khẩn cấp capture."""
        ok, msg = self.client.abort()
        self.lbl_sb_status.setText("Trạng thái: Đã gửi lệnh ABORT")
        QtWidgets.QMessageBox.information(self, "Hủy thu thập", msg)

    def _on_browse_bin(self):
        """Hộp thoại chọn file .bin offline để kiểm thử độc lập."""
        init_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests")
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Chọn tệp dữ liệu Logic Analyzer (.bin)",
            init_dir, "Logic Analyzer Binary Packet (*.bin);;All Files (*)"
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
    # HIỂN THỊ ĐỒ THỊ VÀ GIẢI MÃ
    # =========================================================================

    def _render_capture_data(self, res: Dict[str, Any]):
        """Vẽ dạng sóng 8 kênh và cập nhật thông tin đo kiểm."""
        self.current_data = res
        channels = res["channels"]
        sample_rate = res["sample_rate"]
        sample_count = res["sample_count"]
        trig_offset = res["trig_offset"]
        elapsed_s = res.get("elapsed_s", 0.0)

        # Trục thời gian tính bằng giây (s)
        # N mẫu tương ứng N+1 mốc thời gian cho stepMode=True
        time_axis = np.arange(sample_count + 1, dtype=np.float64) / sample_rate

        # Vẽ từng kênh trên đồ thị
        for ch in range(8):
            ch_data = channels[ch].astype(np.float32)
            y_base = (7 - ch) * 1.5
            y_data = ch_data + y_base
            self.channel_curves[ch].setData(x=time_axis, y=y_data, stepMode="center")

        # Định vị vạch chỉ thị Trigger màu đỏ (tại thời điểm trig_offset)
        trig_time = trig_offset / sample_rate
        self.trigger_line.setValue(trig_time)
        self.trigger_line.show()

        # Tự động zoom vừa vặn trục X
        total_duration = sample_count / sample_rate
        self.plot_widget.setXRange(0, total_duration, padding=0.01)

        # Cập nhật thanh trạng thái
        dur_ms = total_duration * 1000.0
        self.lbl_sb_capture.setText(
            f"Mẫu: {sample_count:,} | Tần số: {sample_rate/1e6:.2f} MHz | Cửa sổ: {dur_ms:.2f} ms"
        )
        self.lbl_sb_status.setText(f"Trạng thái: {res['status_name']} (Truyền: {elapsed_s:.3f} s)")
        self.lbl_sb_checksum.setText(f"Checksum XOR: {'PASS (0x%02X)' % (res.get('payload')[0] if len(res.get('payload')) else 0) if res['checksum_ok'] else 'FAIL'}")

        # Tự động giải mã UART trên kênh được chọn
        self._on_decode_uart()

    def _zoom_fit(self):
        """Khôi phục tầm nhìn toàn bộ dữ liệu mẫu."""
        if self.current_data:
            sample_count = self.current_data["sample_count"]
            sample_rate = self.current_data["sample_rate"]
            self.plot_widget.setXRange(0, sample_count / sample_rate, padding=0.01)

    def _on_frame_clicked(self, row: int, col: int):
        """Khi click vào 1 dòng trong bảng frame, tự động phóng to (zoom) vào vị trí ký tự đó trên đồ thị."""
        if hasattr(self, "current_frames") and 0 <= row < len(self.current_frames):
            f = self.current_frames[row]
            t_start = f["start_time_s"]
            t_stop = f["stop_time_s"]
            duration = max(t_stop - t_start, 0.0001)
            # Thêm lề 35% hai bên để quan sát rõ cả Start bit và Stop bit
            self.plot_widget.setXRange(max(0, t_start - duration * 0.35), t_stop + duration * 0.35, padding=0)

    def _on_decode_uart(self):
        """Thực thi giải mã UART trên kênh được chỉ định."""
        if not self.current_data:
            return

        ch_idx = self.cb_decode_ch.currentData()
        baudrate = self.cb_decode_baud.currentData()
        sample_rate = self.current_data["sample_rate"]
        ch_arr = self.current_data["channels"][ch_idx]
        samples = ch_arr.tolist()

        # Cấu hình decoder
        self.decoder.sample_rate = sample_rate
        self.decoder.baudrate = baudrate

        # Bắt đầu giải mã từ mẫu 0 để quét trọn vẹn toàn bộ 32KB buffer
        decoded_text, frames = self.decoder.decode(samples, start_idx=0)
        self.current_frames = frames

        # 1. Hiển thị chuỗi văn bản ASCII hoặc thông báo chẩn đoán thông minh
        if decoded_text:
            self.txt_decoded.setStyleSheet("color: #00e5ff; font-size: 14px; font-weight: bold;")
            self.txt_decoded.setPlainText(decoded_text)
        else:
            num_ones = int(np.count_nonzero(ch_arr == 1))
            num_zeros = len(ch_arr) - num_ones
            transitions = int(np.count_nonzero(np.diff(ch_arr) != 0))

            self.txt_decoded.setStyleSheet("color: #ffb74d; font-size: 13px; font-family: monospace;")
            if transitions == 0 and num_ones == 0:
                diag_msg = (
                    f"⚠️ KÊNH D{ch_idx} (PA{ch_idx}) ĐANG Ở MỨC LOW (0V) LIÊN TỤC (0 LẦN CHUYỂN MỨC)\n\n"
                    f"🔍 NGUYÊN NHÂN:\n"
                    f"• Chân PA{ch_idx} đang thả nổi với trở kéo xuống nội (Pull-down 0V).\n"
                    f"• Chưa có dây dẫn kết nối nguồn phát tín hiệu vào chân PA{ch_idx}.\n\n"
                    f"🛠️ HƯỚNG DẪN KHẮC PHỤC (Loopback Self-Test):\n"
                    f"1. Hãy cắm 1 sợi dây Jumper nối từ chân PA9 (USART1_TX phát test) sang chân PA0 (Kênh D0).\n"
                    f"2. Chọn Kênh Trigger: 'CH0' | Kiểu Trigger: 'Cạnh xuống (Falling Edge)' hoặc 'Free-run'.\n"
                    f"3. Bấm '▶ Start Capture' một lần nữa để hiển thị chuỗi 'TEST_LA_2026\\r\\n'!"
                )
            elif transitions == 0 and num_zeros == 0:
                diag_msg = (
                    f"⚠️ KÊNH D{ch_idx} (PA{ch_idx}) ĐANG Ở MỨC HIGH (3.3V) LIÊN TỤC (TÍN HIỆU NGHỈ)\n\n"
                    f"🔍 NGUYÊN NHÂN:\n"
                    f"• Đường truyền UART đang ở trạng thái nghỉ (IDLE) nhưng không có ký tự nào được phát.\n\n"
                    f"🛠️ HƯỚNG DẪN KHẮC PHỤC:\n"
                    f"1. Kiểm tra nguồn phát UART (hoặc MCU) có đang thực sự truyền dữ liệu không.\n"
                    f"2. Đổi Kiểu Trigger sang 'Cạnh xuống (Falling Edge)' để đợi khi có ký tự mới bắt đầu ghi."
                )
            elif transitions > 0:
                samples_per_bit = sample_rate / baudrate
                diag_msg = (
                    f"⚠️ PHÁT HIỆN {transitions:,} LẦN CHUYỂN MỨC TRÊN D{ch_idx} NHƯNG KHÔNG GIẢI MÃ ĐƯỢC UART\n\n"
                    f"🔍 THÔNG SỐ HIỆN TẠI:\n"
                    f"• Tốc độ Baud: {baudrate:,} bps | Tần số lấy mẫu: {sample_rate/1e6:.2f} MHz ({samples_per_bit:.1f} mẫu/bit)\n\n"
                    f"🛠️ HƯỚNG DẪN KHẮC PHỤC:\n"
                    f"1. Kiểm tra Tốc độ Baud ({baudrate} bps) có khớp với nguồn phát không (Ví dụ: 115200 bps).\n"
                    f"2. Đảm bảo tần số lấy mẫu đủ lớn (khuyến nghị ≥ 1 MHz cho 115.200 bps).\n"
                    f"3. Kiểm tra chọn đúng kênh nhận tín hiệu ({self.cb_decode_ch.currentText()})."
                )
            else:
                diag_msg = "[Không phát hiện frame UART hợp lệ]"

            self.txt_decoded.setPlainText(diag_msg)

        # 2. Điền dữ liệu vào bảng danh sách khung
        self.table_frames.setRowCount(len(frames))
        for row, f in enumerate(frames):
            time_ms = f["start_time_s"] * 1000.0
            self.table_frames.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))
            self.table_frames.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{time_ms:.3f} ms"))
            self.table_frames.setItem(row, 2, QtWidgets.QTableWidgetItem(str(f["start_sample"])))
            
            char_disp = repr(f["char"])[1:-1]  # Bỏ dấu nháy
            self.table_frames.setItem(row, 3, QtWidgets.QTableWidgetItem(char_disp))
            self.table_frames.setItem(row, 4, QtWidgets.QTableWidgetItem(f"0x{f['byte_val']:02X}"))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
