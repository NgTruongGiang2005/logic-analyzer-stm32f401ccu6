#!/usr/bin/env python3
"""software/gui/main_window.py
Giao diện người dùng Desktop chuẩn thương mại công nghiệp (Saleae Logic 2 / DSView):
- Cấu trúc chuẩn theo UI_SPEC.md và proto.py (v3):
  + Menu Bar: File, Edit, Capture, Measure, View, Help
  + Waveform Viewport (Vùng sóng chiếm ưu thế): Cột nhãn 194px + PlotWidget 8 kênh co giãn lấp đầy
  + Panel phải (313px): Analyzers, Trigger View card thu gọn, Data Table 4 cột, Tìm kiếm
  + Dải Action Rail bên phải (65px): Nút Start tròn xanh lá (Ø 50px) + các icon công cụ
  + Thanh đáy (42px): Session tabs (Session 0, Session 1, +) + Trạng thái kết nối + Mức zoom
- Giao thức nhị phân chuẩn spec/protocol.md (Khung lệnh 5B, Data Frame 32.776B)
- Tích hợp bộ giải mã UART trực tiếp trên sóng (ô bo góc + chấm tâm bit) và bảng gói tin.
"""

import os
import sys
import time
import numpy as np
from typing import Optional, Dict, Any, List

# Khử cảnh báo Wayland requestActivate() trên Linux
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland=false")

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from software.ui import theme as T
from software.gui.logic_client import LogicAnalyzerClient
from software.gui.waveform_widget import WaveformWidget
from software.decoders.uart_decoder import UARTDecoder
from software.decoders.i2c_decoder import I2CDecoder
from software.decoders.spi_decoder import SPIDecoder
from software.utils.exporter import export_image, export_csv, export_vcd
from software.protocol import capture_bytes, parse_capture
import json

# Bảng tra cứu tốc độ lấy mẫu (spec/protocol.md Table 2)
RATE_OPTIONS = [
    ("6 MHz", 6_000_000, 0),
    ("3 MHz", 3_000_000, 1),
    ("2 MHz", 2_000_000, 2),
    ("1 MHz (Mặc định)", 1_000_000, 3),
    ("500 kHz", 500_000, 4),
    ("200 kHz", 200_000, 5),
    ("100 kHz", 100_000, 6),
    ("50 kHz", 50_000, 7),
    ("10 kHz", 10_000, 8),
]


class CaptureWorker(QtCore.QThread):
    """Luồng phụ thu thập dữ liệu serial ngầm không gây block UI."""
    capture_done = QtCore.pyqtSignal(dict)
    capture_error = QtCore.pyqtSignal(str)
    phase_changed = QtCore.pyqtSignal(str)

    def __init__(self, client: LogicAnalyzerClient, rate_idx: int, trig_ch: int, trig_mode: int, task='capture'):
        super().__init__()
        self.client = client
        self.rate_idx = rate_idx
        self.trig_ch = trig_ch
        self.trig_mode = trig_mode
        self.task = task

    def run(self):
        try:
            if self.task == 'ping':
                ok, message = self.client.ping()
                self.capture_done.emit(dict(ping=True, success=ok, message=message))
                return
            res = self.client.start_capture(
                rate_idx=self.rate_idx,
                trig_ch=self.trig_ch,
                trig_mode=self.trig_mode,
                phase_callback=self.phase_changed.emit
            )
            if res.get("success", False) or res.get('aborted'):
                self.capture_done.emit(res)
            else:
                self.capture_error.emit(res.get("error", "Lỗi thu thập dữ liệu"))
        except Exception as e:
            self.capture_error.emit(str(e))


class MainWindow(QtWidgets.QMainWindow):
    """Cửa sổ chính Desktop chuẩn Saleae Logic 2 theo UI_SPEC.md."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HUST Logic Analyzer — 8 Channels / 6 MHz")
        self.resize(1280, 860)
        self.setMinimumSize(1080, 600)
        self.setStyleSheet(T.QSS)

        # Lớp Client & Worker
        self.client = LogicAnalyzerClient()
        self.worker: Optional[CaptureWorker] = None
        self._busy = False
        self._closing = False
        self.analyzer = dict(kind='UART', channel=0, baudrate=115200, scl=1, sda=2,
                             sck=1, mosi=2, miso=3, cs=4, mode=0, bit_order='MSB', cs_active='LOW')
        self._sessions = [None]

        # Bộ giải mã
        self.uart_decoder = UARTDecoder(sample_rate=1_000_000, baudrate=115200)
        self.i2c_decoder = I2CDecoder(sample_rate=1_000_000)
        self.spi_decoder = SPIDecoder(sample_rate=1_000_000)

        # Dữ liệu hiện hành
        self.current_data: Optional[Dict[str, Any]] = None
        self.current_uart_frames: List[Dict[str, Any]] = []

        # Các widget điều khiển kênh hỗ trợ tương thích ngược
        self.ch_edits: List[QtWidgets.QLineEdit] = []
        self.ch_checks: List[QtWidgets.QCheckBox] = []
        for i in range(8):
            ed = QtWidgets.QLineEdit(f"Channel {i}")
            ed.textChanged.connect(lambda txt, ch=i: self._on_channel_name_changed(ch))
            self.ch_edits.append(ed)

            chk = QtWidgets.QCheckBox()
            chk.setChecked(True)
            chk.stateChanged.connect(lambda st, ch=i: self._on_channel_visibility_changed(ch, st))
            self.ch_checks.append(chk)

        # Khởi tạo giao diện
        self._init_layout()
        self._init_menu_bar()
        self._refresh_ports()

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

        # Nạp dữ liệu giả lập ban đầu để sẵn sàng hiển thị ngay khi mở
        sample_file = os.path.join(os.path.dirname(__file__), "..", "tests", "sample_data_1mhz.bin")
        if os.path.exists(sample_file):
            self._load_bin_file(sample_file)

    # =========================================================================
    # THANH MENU (FILE / EDIT / CAPTURE / MEASURE / VIEW / HELP)
    # =========================================================================

    def _init_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #ffffff;
                color: #1b1b1c;
                border-bottom: 1px solid #57575e;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
                padding: 2px 6px;
            }
            QMenuBar::item {
                background: transparent;
                color: #1b1b1c;
                padding: 4px 10px;
                margin-right: 4px;
            }
            QMenuBar::item:selected {
                background-color: #e4e4e7;
                border-radius: 4px;
            }
            QMenu {
                background-color: #ffffff;
                color: #1b1b1c;
                border: 1px solid #d4d4d8;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 16px;
                color: #1b1b1c;
            }
            QMenu::item:selected {
                background-color: #e4e4e7;
                color: #1b1b1c;
                border-radius: 3px;
            }
        """)

        # File
        menu_file = menubar.addMenu("&File")
        act_open = QtWidgets.QAction("&Open Capture (.bin)...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_capture_file)
        self.act_open = act_open
        menu_file.addAction(act_open)

        self.act_save = menu_file.addAction('Save Capture (.lacapture)...', self._save_capture_file)
        self.act_save.setShortcut('Ctrl+Shift+S')

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

        # Edit
        menu_edit = menubar.addMenu("&Edit")
        act_reset_cursors = QtWidgets.QAction("&Reset Cursors", self)
        act_reset_cursors.triggered.connect(lambda: self.waveform.set_cursor_positions(0.0, 8.68e-5))
        menu_edit.addAction(act_reset_cursors)

        # Capture
        menu_capture = menubar.addMenu("&Capture")
        act_start = QtWidgets.QAction("&Start Capture", self)
        act_start.setShortcut("F5")
        act_start.triggered.connect(self._on_start_capture)
        self.act_start = act_start
        menu_capture.addAction(act_start)

        act_abort = QtWidgets.QAction("&Abort Capture", self)
        act_abort.setShortcut("Escape")
        act_abort.triggered.connect(self._on_abort)
        self.act_abort = act_abort
        self.act_abort.setEnabled(False)
        menu_capture.addAction(act_abort)

        act_ping = QtWidgets.QAction("Check Connection (&Ping)", self)
        act_ping.triggered.connect(self._on_ping)
        self.act_ping = act_ping
        menu_capture.addAction(act_ping)

        # Measure
        menu_measure = menubar.addMenu("&Measure")
        act_toggle_cursors = QtWidgets.QAction("Toggle &Cursors (A & B)", self)
        act_toggle_cursors.setShortcut("C")
        act_toggle_cursors.triggered.connect(lambda: self.waveform.toggle_cursors())
        menu_measure.addAction(act_toggle_cursors)

        # View
        menu_view = menubar.addMenu("&View")
        act_zoom_fit = QtWidgets.QAction("&Zoom Fit", self)
        act_zoom_fit.setShortcut("Ctrl+F")
        act_zoom_fit.triggered.connect(self.waveform.zoom_fit)
        menu_view.addAction(act_zoom_fit)
        menu_view.addAction('Channel settings...', self._channel_settings)

        # Help
        menu_help = menubar.addMenu("&Help")
        act_about = QtWidgets.QAction("&About Logic Analyzer", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    def _show_about(self):
        QtWidgets.QMessageBox.about(
            self,
            "About HUST Logic Analyzer",
            "<h3>HUST Logic Analyzer (8 Channels, 6 MHz)</h3>"
            "<p><b>PC Software (TV3):</b> Nguyen Truong Giang</p>"
            "<p><b>Platform:</b> STM32F401CCU6 WeAct Black Pill V3.0 (84 MHz Clock Tree)</p>"
            "<p><b>SSoT Protocol:</b> spec/protocol.md (32,776 B Data Frame, XOR Checksum)</p>"
            "<p><b>Design Spec:</b> docs/UI_SPEC.md (Saleae Logic 2 Commercial Standard)</p>"
            "<p>Hanoi University of Science and Technology (HUST) - 2026</p>"
        )

    # =========================================================================
    # BỐ CỤC CHÍNH (MAIN BODY + RIGHT PANEL + RAIL + BOTTOM BAR)
    # =========================================================================

    def _init_layout(self):
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Vùng thân (Horizontal layout)
        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        # 1. Khung vẽ sóng (Waveform Widget)
        self.waveform = WaveformWidget(self)
        body.addWidget(self.waveform, 1)

        # 2. Panel phải (Analyzers / Trigger View / Data Table - 313 px)
        self.right_panel = self._create_right_panel()
        body.addWidget(self.right_panel)

        # 3. Dải Action Rail bên phải (Nút Start tròn Ø 50px - 65 px)
        self.rail = self._create_rail()
        body.addWidget(self.rail)

        # 4. Thanh đáy (Tab Session + Mức zoom - 42 px)
        self.bottom_bar = self._create_bottom_bar()
        outer.addWidget(self.bottom_bar)
        self.waveform.vb.sigXRangeChanged.connect(
            lambda _vb, r: self.lbl_zoom.setText(self.waveform.format_time(r[1] - r[0])))

    # =========================================================================
    # PANEL PHẢI (313 PX)
    # =========================================================================

    def _create_right_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget(self)
        panel.setFixedWidth(T.RIGHT_PANEL_WIDTH)
        panel.setStyleSheet(f"background-color: {T.BG_MAIN}; border-left: 1px solid {T.BORDER};")

        v_layout = QtWidgets.QVBoxLayout(panel)
        v_layout.setContentsMargins(12, 10, 12, 10)
        v_layout.setSpacing(8)

        # 1. Phần Analyzers
        h_ana = QtWidgets.QHBoxLayout()
        lbl_ana = QtWidgets.QLabel("Analyzers")
        lbl_ana.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {T.TEXT};")
        btn_add_ana = QtWidgets.QPushButton("+")
        btn_add_ana.setFixedSize(24, 24)
        btn_add_ana.setStyleSheet(f"font-size: 14px; font-weight: bold; padding: 0px;")
        btn_add_ana.clicked.connect(self._on_add_analyzer_dialog)
        h_ana.addWidget(lbl_ana)
        h_ana.addStretch(1)
        h_ana.addWidget(btn_add_ana)
        v_layout.addLayout(h_ana)

        # Mục analyzer đang kích hoạt
        self.lbl_ana_item = QtWidgets.QLabel(
            f"<span style='color:{T.DECODE_UART_BG}'>■</span> &nbsp;Async Serial &nbsp;"
            f"<span style='color:{T.ACCENT_START}'>✔</span>"
        )
        self.lbl_ana_item.setStyleSheet(f"font-size: 13px; color: {T.TEXT}; padding: 2px 4px;")
        v_layout.addWidget(self.lbl_ana_item)

        # 2. Thẻ thu gọn "Trigger View" (Card)
        self.card_trigger = QtWidgets.QFrame()
        self.card_trigger.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_CARD};
                border: 1px solid {T.BORDER};
                border-radius: 6px;
            }}
        """)
        card_v = QtWidgets.QVBoxLayout(self.card_trigger)
        card_v.setContentsMargins(10, 8, 10, 8)
        card_v.setSpacing(6)

        # Header của Card Trigger View
        card_h = QtWidgets.QHBoxLayout()
        self.lbl_card_title = QtWidgets.QLabel("› Trigger View ⚠")
        self.lbl_card_title.setStyleSheet("font-weight: bold; color: #f9b353;")
        self.btn_close_card = QtWidgets.QPushButton("✕")
        self.btn_close_card.setFixedSize(20, 20)
        self.btn_close_card.setStyleSheet(f"background: {T.BG_SELECT}; border-radius: 10px; padding: 0px;")
        self.btn_close_card.clicked.connect(self._toggle_trigger_card)
        card_h.addWidget(self.lbl_card_title)
        card_h.addStretch(1)
        card_h.addWidget(self.btn_close_card)
        card_v.addLayout(card_h)

        # Nội dung thiết lập Trigger & Cổng kết nối bên trong Card
        self.trigger_body = QtWidgets.QWidget()
        trig_layout = QtWidgets.QVBoxLayout(self.trigger_body)
        trig_layout.setContentsMargins(0, 4, 0, 0)
        trig_layout.setSpacing(6)

        # Cổng COM/ACM
        h_port = QtWidgets.QHBoxLayout()
        self.combo_ports = QtWidgets.QComboBox()
        self.combo_ports.setEditable(True)
        self.combo_ports.setToolTip('Chọn COM hoặc nhập socket://127.0.0.1:8765 để thử mock TCP')
        self.btn_refresh = QtWidgets.QPushButton("⟳")
        self.btn_refresh.setFixedWidth(28)
        self.btn_refresh.setToolTip("Quét lại danh sách cổng serial")
        self.btn_refresh.clicked.connect(self._refresh_ports)
        h_port.addWidget(self.combo_ports, 1)
        h_port.addWidget(self.btn_refresh)
        trig_layout.addLayout(h_port)

        # Tần số lấy mẫu
        h_rate = QtWidgets.QHBoxLayout()
        lbl_rate = QtWidgets.QLabel("Rate:")
        lbl_rate.setStyleSheet(f"color: {T.TEXT_DIM};")
        self.combo_rate = QtWidgets.QComboBox()
        for label, val, idx in RATE_OPTIONS:
            self.combo_rate.addItem(label, idx)
        self.combo_rate.setCurrentIndex(3)  # Mặc định 1 MHz
        h_rate.addWidget(lbl_rate)
        h_rate.addWidget(self.combo_rate, 1)
        trig_layout.addLayout(h_rate)

        # Kênh Trigger & Chế độ
        h_trig = QtWidgets.QHBoxLayout()
        self.combo_ch = QtWidgets.QComboBox()
        for i in range(8):
            self.combo_ch.addItem(f"CH{i} (D{i})", i)
        self.combo_ch.setCurrentIndex(0)

        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItem("Free-run", 0)
        self.combo_mode.addItem("Rising ↑", 1)
        self.combo_mode.addItem("Falling ↓", 2)
        self.combo_mode.setCurrentIndex(2)  # Mặc định Falling PA0
        h_trig.addWidget(self.combo_ch)
        h_trig.addWidget(self.combo_mode)
        trig_layout.addLayout(h_trig)

        # Checkbox Offline Mock
        self.chk_mock = QtWidgets.QCheckBox("Offline Mock (Test file .bin)")
        self.chk_mock.setStyleSheet(f"color: {T.TEXT_DIM}; font-size: 11px;")
        trig_layout.addWidget(self.chk_mock)

        card_v.addWidget(self.trigger_body)
        v_layout.addWidget(self.card_trigger)

        # 3. Phần Data Table
        d_header = QtWidgets.QHBoxLayout()
        d_title = QtWidgets.QLabel(f"Data &nbsp;<span style='color:{T.ACCENT_START}'>✔</span>")
        d_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {T.TEXT};")
        d_header.addWidget(d_title)
        d_header.addStretch(1)
        v_layout.addLayout(d_header)

        # Ô tìm kiếm gói tin
        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("Type to search")
        self.edit_search.textChanged.connect(self._filter_packet_table)
        v_layout.addWidget(self.edit_search)

        # Bảng dữ liệu gói tin 4 cột theo proto.py v3: [■ | Type | Start | Duration]
        self.table_uart_packets = QtWidgets.QTableWidget(0, 4)
        self.table_uart_packets.setHorizontalHeaderLabels(["", "Type", "Start", "Duration"])
        self.table_uart_packets.verticalHeader().setVisible(False)
        self.table_uart_packets.setAlternatingRowColors(True)
        self.table_uart_packets.setShowGrid(False)
        self.table_uart_packets.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_uart_packets.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_uart_packets.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_uart_packets.horizontalHeader().setStretchLastSection(True)
        self.table_uart_packets.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.table_uart_packets.setColumnWidth(0, 26)
        self.table_uart_packets.setColumnWidth(1, 64)
        self.table_uart_packets.setColumnWidth(2, 95)
        self.table_uart_packets.cellClicked.connect(self._on_table_row_clicked)
        v_layout.addWidget(self.table_uart_packets, 1)

        # Terminal hiển thị chuỗi ASCII (hỗ trợ kiểm thử tự động)
        self.txt_uart_decoded = QtWidgets.QTextEdit()
        self.txt_uart_decoded.setReadOnly(True)
        self.txt_uart_decoded.setFixedHeight(75)
        self.txt_uart_decoded.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_DEEP};
                color: #38bdf8;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                border: 1px solid {T.BORDER};
            }}
        """)
        v_layout.addWidget(self.txt_uart_decoded)

        return panel

    # =========================================================================
    # DẢI ACTION RAIL BÊN PHẢI (65 PX)
    # =========================================================================

    def _create_rail(self) -> QtWidgets.QWidget:
        rail = QtWidgets.QWidget(self)
        rail.setFixedWidth(T.RAIL_WIDTH)
        rail.setStyleSheet(f"background-color: {T.BG_MAIN}; border-left: 1px solid {T.BORDER};")

        v_layout = QtWidgets.QVBoxLayout(rail)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        # 1. Khoảng cách đỉnh tới nút Start
        v_layout.addSpacing(22)

        # 2. Nút Start tròn màu xanh lá (Ø 50px)
        self.btn_rail_start = QtWidgets.QPushButton("▶")
        self.btn_rail_start.setObjectName("startButton")
        self.btn_rail_start.setFixedSize(50, 50)
        self.btn_rail_start.setToolTip("Bắt đầu lấy mẫu (F5)")
        self.btn_rail_start.setStyleSheet(f"""
            QPushButton#startButton {{
                background-color: {T.ACCENT_START};
                border: none;
                border-radius: 25px;
                color: #ffffff;
                font-size: 18px;
                padding-left: 2px;
            }}
            QPushButton#startButton:hover {{
                background-color: #38b457;
            }}
        """)
        self.btn_rail_start.clicked.connect(self._on_start_capture)
        v_layout.addWidget(self.btn_rail_start, 0, QtCore.Qt.AlignHCenter)

        # 3. Khoảng cách tới icon Thiết bị
        v_layout.addSpacing(34)
        self.btn_rail_dev = QtWidgets.QToolButton()
        self.btn_rail_dev.setText("▭")
        self.btn_rail_dev.setToolTip("Thiết bị & Cấu hình Trigger")
        self.btn_rail_dev.setStyleSheet(f"QToolButton {{ border: none; color: {T.TEXT_DIM}; font-size: 22px; }}")
        self.btn_rail_dev.clicked.connect(self._toggle_trigger_card)
        v_layout.addWidget(self.btn_rail_dev, 0, QtCore.Qt.AlignHCenter)

        # 4. Khoảng cách tới mục Active Analyzers
        v_layout.addSpacing(22)
        card_active = QtWidgets.QFrame()
        card_active.setFixedHeight(64)
        card_active.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_SELECT};
                border-left: 3px solid #ffffff;
                border-top: none; border-right: none; border-bottom: none;
            }}
        """)
        c_lay = QtWidgets.QVBoxLayout(card_active)
        c_lay.setContentsMargins(0, 0, 0, 0)
        self.btn_rail_ana = QtWidgets.QLabel("1F")
        self.btn_rail_ana.setAlignment(QtCore.Qt.AlignCenter)
        self.btn_rail_ana.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 16px; border: none; background: transparent;")
        c_lay.addWidget(self.btn_rail_ana)
        v_layout.addWidget(card_active)

        # 5. Khoảng cách tới icon Cursors / Đo đạc
        v_layout.addSpacing(32)
        self.btn_rail_ruler = QtWidgets.QToolButton()
        self.btn_rail_ruler.setText("📐")
        self.btn_rail_ruler.setToolTip("Bật/Tắt Cặp thước đo thời gian A & B (C)")
        self.btn_rail_ruler.setStyleSheet("QToolButton { border: none; font-size: 18px; }")
        self.btn_rail_ruler.clicked.connect(lambda: self.waveform.toggle_cursors())
        v_layout.addWidget(self.btn_rail_ruler, 0, QtCore.Qt.AlignHCenter)

        # 6. Khoảng cách tới icon Bố cục
        v_layout.addSpacing(46)
        self.btn_rail_grid = QtWidgets.QToolButton()
        self.btn_rail_grid.setText("▦")
        self.btn_rail_grid.setToolTip("Xuất báo cáo & Dữ liệu (Ctrl+S)")
        self.btn_rail_grid.setStyleSheet(f"QToolButton {{ border: none; color: {T.TEXT_DIM}; font-size: 22px; }}")
        self.btn_rail_grid.clicked.connect(self._export_image)
        v_layout.addWidget(self.btn_rail_grid, 0, QtCore.Qt.AlignHCenter)

        # Đẩy cụm icon đáy xuống cuối
        v_layout.addStretch(1)

        # 7. Icon phản hồi / Chat
        self.btn_rail_chat = QtWidgets.QToolButton()
        self.btn_rail_chat.setText("💬")
        self.btn_rail_chat.setToolTip("Phản hồi & Trợ giúp")
        self.btn_rail_chat.setStyleSheet("QToolButton { border: none; font-size: 18px; }")
        self.btn_rail_chat.clicked.connect(self._show_about)
        v_layout.addWidget(self.btn_rail_chat, 0, QtCore.Qt.AlignHCenter)
        v_layout.addSpacing(32)

        # 8. Icon Menu 3 gạch
        self.btn_rail_menu = QtWidgets.QToolButton()
        self.btn_rail_menu.setText("☰")
        self.btn_rail_menu.setToolTip("Menu tác vụ")
        self.btn_rail_menu.setStyleSheet(f"QToolButton {{ border: none; color: {T.TEXT_DIM}; font-size: 22px; }}")
        self.btn_rail_menu.clicked.connect(self._show_about)
        v_layout.addWidget(self.btn_rail_menu, 0, QtCore.Qt.AlignHCenter)
        v_layout.addSpacing(14)

        return rail

    # =========================================================================
    # THANH ĐÁY (42 PX)
    # =========================================================================

    def _create_bottom_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget(self)
        bar.setFixedHeight(T.BOTTOM_BAR_HEIGHT)
        bar.setStyleSheet(f"""
            QWidget {{
                background-color: {T.BG_MAIN};
                border-top: 1px solid {T.BORDER};
            }}
            QTabBar::tab {{
                background: {T.BG_MAIN};
                color: {T.TEXT_DIM};
                padding: 0px 16px;
                height: {T.BOTTOM_BAR_HEIGHT - 1}px;
                border-top: 3px solid transparent;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: #ffffff;
                border-top: 3px solid #ffffff;
            }}
        """)

        h_layout = QtWidgets.QHBoxLayout(bar)
        h_layout.setContentsMargins(0, 0, 16, 0)
        h_layout.setSpacing(12)

        # Tab Session bên trái
        self.tab_sessions = QtWidgets.QTabBar()
        self.tab_sessions.setExpanding(False)
        self.tab_sessions.addTab("Session 0")
        self.tab_sessions.addTab("+")
        self.tab_sessions.setCurrentIndex(0)
        self.tab_sessions.currentChanged.connect(self._switch_session)
        h_layout.addWidget(self.tab_sessions)

        # Trạng thái kết nối ở giữa
        self.lbl_status = QtWidgets.QLabel("Ready | Offline Mock available")
        self.lbl_status.setStyleSheet(f"color: {T.TEXT_DIM}; font-size: 12px; background: transparent; border: none;")
        h_layout.addWidget(self.lbl_status)

        h_layout.addStretch(1)

        # Mức thu phóng ở góc phải
        self.lbl_zoom = QtWidgets.QLabel("128 µs ^")
        self.lbl_zoom.setStyleSheet(f"color: {T.TEXT_DIM}; font-size: 13px; font-family: 'Segoe UI'; background: transparent; border: none;")
        h_layout.addWidget(self.lbl_zoom)

        return bar

    # =========================================================================
    # CÁC HÀNH ĐỘNG ĐIỀU KHIỂN & SỰ KIỆN
    # =========================================================================

    def _toggle_trigger_card(self):
        """Ẩn/hiện nội dung Card Trigger View."""
        visible = not self.trigger_body.isVisible()
        self.trigger_body.setVisible(visible)
        self.lbl_card_title.setText("› Trigger View ⚠" if visible else "› Trigger View (Hidden)")

    def _refresh_ports(self):
        """Quét và làm mới danh sách cổng serial USB-CDC."""
        self.combo_ports.clear()
        ports = self.client.list_ports()
        if ports:
            for item in ports:
                if isinstance(item, (tuple, list)):
                    p_dev, p_desc = item[0], item[1]
                else:
                    p_dev, p_desc = str(item), str(item)
                self.combo_ports.addItem(p_desc, p_dev)
            self.lbl_status.setText(f"Tìm thấy {len(ports)} cổng serial USB-CDC")
        else:
            self.combo_ports.addItem("Không tìm thấy kit USB", None)
            self.lbl_status.setText("Chưa cắm kit STM32 (Bật 'Offline Mock' để test)")

    def _selected_port(self):
        if self.chk_mock.isChecked():
            return 'OFFLINE_MOCK'
        # Editable combo boxes must honor manually entered paths/URLs.
        i = self.combo_ports.currentIndex()
        if i >= 0 and self.combo_ports.currentText() == self.combo_ports.itemText(i):
            return self.combo_ports.itemData(i)
        return self.combo_ports.currentText().strip()

    def _set_busy(self, busy):
        self._busy = busy
        for widget in (self.btn_rail_start, self.combo_ports, self.combo_rate, self.combo_ch,
                       self.combo_mode, self.chk_mock, self.btn_refresh, self.tab_sessions):
            widget.setEnabled(not busy)
        for action in (self.act_start, self.act_ping, self.act_open, self.act_save):
            action.setEnabled(not busy)
        self.act_abort.setEnabled(busy and self.worker is not None and self.worker.task == 'capture')

    def _begin_job(self, task):
        if self._busy:
            return
        port = self._selected_port()
        if not port:
            self.lbl_status.setText('Chọn cổng serial hoặc Offline Mock trước.')
            return
        ok, msg = self.client.connect(port)
        if not ok:
            QtWidgets.QMessageBox.critical(self, 'Lỗi kết nối', msg)
            return
        self.worker = CaptureWorker(self.client, self.combo_rate.currentData(),
                                    self.combo_ch.currentData(), self.combo_mode.currentData(), task)
        self.worker.capture_done.connect(self._on_capture_done)
        self.worker.capture_error.connect(self._on_capture_error)
        self.worker.phase_changed.connect(self._on_capture_phase)
        self.worker.finished.connect(self._on_worker_finished)
        self._set_busy(True)
        self.lbl_status.setText('Đang kiểm tra kết nối...' if task == 'ping' else f'Đang chờ capture: {port}...')
        self.worker.start()

    def _on_ping(self):
        self._begin_job('ping')

    def _on_start_capture(self):
        self._begin_job('capture')

    def _on_capture_phase(self, phase):
        if phase == 'receiving':
            self.act_abort.setEnabled(False)
            self.lbl_status.setText('Đang nhận 32,776 bytes — khóa lệnh cho tới khi nhận xong.')

    def _on_capture_done(self, res):
        if self._closing:
            return
        if res.get('ping'):
            self.lbl_status.setText(f"Connected ({res['message']})" if res['success'] else f"PING thất bại: {res['message']}")
        elif res.get('aborted'):
            self.lbl_status.setText('Capture aborted — đã nhận xác nhận từ thiết bị.')
        else:
            self._render_capture_data(res)

    def _on_capture_error(self, err_msg):
        if not self._closing:
            self.lbl_status.setText(f'Lỗi: {err_msg}')
            QtWidgets.QMessageBox.critical(self, 'Lỗi lấy mẫu', err_msg)

    def _on_worker_finished(self):
        self.client.disconnect()
        worker, self.worker = self.worker, None
        self._set_busy(False)
        if worker:
            worker.deleteLater()
        if self._closing:
            self.close()

    def _on_abort(self):
        if not self._busy or not self.worker or self.worker.task != 'capture':
            return
        if self.client.receiving_payload:
            self.lbl_status.setText('Đang truyền dữ liệu; không thể gửi Abort trong trạng thái TRANSFERRING.')
            return
        self.client.request_abort()
        self.act_abort.setEnabled(False)
        self.lbl_status.setText('Đã yêu cầu Abort; đang chờ phản hồi hoặc gói dữ liệu hoàn tất.')

    def closeEvent(self, event):
        if self._busy:
            self._closing = True
            self._on_abort()
            event.ignore()
            return
        self.client.disconnect()
        event.accept()

    def _render_capture_data(self, res: dict):
        """Hiển thị kết quả thu thập dữ liệu và giải mã protocol."""
        self.current_data = res
        self.waveform.render_data(res)

        fs = float(res.get("sample_rate", 1_000_000))
        status_name = res.get("status_name", "Triggered")
        elapsed = res.get("elapsed_s", 0.0)

        rate_str = f"{fs/1e6:.1f} MHz" if fs >= 1e6 else f"{fs/1e3:.0f} kHz"
        self.lbl_status.setText(f"Hoàn tất: 32,768 mẫu ({rate_str}) | {status_name} trong {elapsed:.3f} s")

        # Tự động giải mã UART trên Kênh 0
        self._decode_uart()

    def _decode_uart(self):
        """Decode the full capture, including valid data before the trigger."""
        if not self.current_data:
            return
        channels = self.current_data['channels']
        fs = float(self.current_data['sample_rate'])
        offset = int(self.current_data['trig_offset'])
        a = self.analyzer
        kind = a['kind']
        if kind == 'UART':
            self.uart_decoder.sample_rate = fs
            self.uart_decoder.baudrate = a['baudrate']
            text, frames = self.uart_decoder.decode(channels[a['channel']])
            channel = a['channel']
        elif kind == 'I2C':
            self.i2c_decoder.sample_rate = fs
            text, frames = self.i2c_decoder.decode(channels[a['scl']], channels[a['sda']])
            channel = a['sda']
        else:
            self.spi_decoder = SPIDecoder(fs, a['mode'] // 2, a['mode'] % 2, a['bit_order'], a['cs_active'])
            text, frames = self.spi_decoder.decode(channels[a['sck']], channels[a['mosi']],
                                                  channels[a['miso']], channels[a['cs']])
            channel = a['mosi']
        self.current_uart_frames = frames  # Compatibility: selected analyzer's packets.
        self.txt_uart_decoded.setPlainText(text)
        self.lbl_ana_item.setText(f"{kind} · D{channel} · {len(frames)} packets")
        self.waveform.set_analyzer_channel(channel, 'Async Serial' if kind == 'UART' else kind)
        self.table_uart_packets.setRowCount(len(frames))
        for row, frame in enumerate(frames):
            begin, finish = frame['start_sample'], frame['stop_sample']
            description = frame.get('type', 'data').lower()
            if kind == 'UART':
                detail = f"Hex: 0x{frame['byte_val']:02X} | ASCII: {frame['char']!r}"
                frame['label'] = f"0x{frame['byte_val']:02X}"
            elif kind == 'I2C':
                detail = frame['desc'] + (' ACK' if frame['ack'] else ' NACK')
                frame['label'] = frame['desc']
            else:
                detail = f"MOSI {frame['mosi_hex']} / MISO {frame['miso_hex']}"
                frame['label'] = detail
            values = ['■', description, self.waveform.format_time((begin-offset)/fs),
                      self.waveform.format_time((finish-begin)/fs)]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(detail)
                if col == 0:
                    item.setForeground(QtGui.QBrush(QtGui.QColor(T.DECODE_UART_BG)))
                self.table_uart_packets.setItem(row, col, item)
            self.table_uart_packets.item(row, 1).setData(QtCore.Qt.UserRole, (begin/fs, finish/fs))
        self.waveform.render_uart_decorations(frames, fs, offset, channel, a['baudrate'] if kind == 'UART' else None)
        self._filter_packet_table(self.edit_search.text())

    def _filter_packet_table(self, query: str):
        """Lọc các hàng trong bảng dữ liệu theo chuỗi tìm kiếm."""
        q = query.strip().lower()
        for r in range(self.table_uart_packets.rowCount()):
            match = False
            for c in range(1, self.table_uart_packets.columnCount()):
                item = self.table_uart_packets.item(r, c)
                if item and (q in item.text().lower() or (item.toolTip() and q in item.toolTip().lower())):
                    match = True
                    break
            self.table_uart_packets.setRowHidden(r, not match and len(q) > 0)

    def _on_table_row_clicked(self, row: int, col: int):
        """Khi bấm vào một hàng trong bảng, phóng to và căn giữa byte đó trên sóng."""
        item = self.table_uart_packets.item(row, 1)
        if item:
            data = item.data(QtCore.Qt.UserRole)
            if data:
                t_start_abs, t_stop_abs = data
                self.waveform.zoom_to_window(t_start_abs, t_stop_abs)

    def _on_channel_name_changed(self, ch: int):
        if 0 <= ch < 8:
            new_name = self.ch_edits[ch].text().strip()
            self.waveform.set_channel_name(ch, new_name)

    def _on_channel_visibility_changed(self, ch: int, state):
        if 0 <= ch < 8:
            visible = (state == QtCore.Qt.Checked or state == 1 or state is True)
            self.waveform.set_channel_visible(ch, visible)

    def _on_decode_uart(self):
        self._decode_uart()

    def _on_add_analyzer_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle('Configure analyzer')
        form = QtWidgets.QFormLayout(dialog)
        fields = {}
        choices = dict(kind=['UART', 'I2C', 'SPI'], mode=[0, 1, 2, 3],
                       bit_order=['MSB', 'LSB'], cs_active=['LOW', 'HIGH'])
        labels = dict(kind='Protocol', channel='UART channel', baudrate='UART baudrate',
                      scl='I2C SCL', sda='I2C SDA', sck='SPI SCK', mosi='SPI MOSI',
                      miso='SPI MISO', cs='SPI CS', mode='SPI mode', bit_order='SPI bit order', cs_active='SPI CS active')
        for key, value in self.analyzer.items():
            if key == 'baudrate':
                widget = QtWidgets.QSpinBox()
                widget.setRange(1, 3000000)
                widget.setValue(value)
            else:
                widget = QtWidgets.QComboBox()
                for option in choices.get(key, list(range(8))):
                    widget.addItem(str(option) if key in choices else f'D{option}', option)
                widget.setCurrentIndex(widget.findData(value))
            fields[key] = widget
            form.addRow(labels[key], widget)
        def update_fields():
            kind = fields['kind'].currentData()
            relevant = {'UART': ['channel', 'baudrate'], 'I2C': ['scl', 'sda'],
                        'SPI': ['sck', 'mosi', 'miso', 'cs', 'mode', 'bit_order', 'cs_active']}[kind]
            for key, widget in fields.items():
                if key != 'kind':
                    widget.setVisible(key in relevant)
                    form.labelForField(widget).setVisible(key in relevant)
        fields['kind'].currentIndexChanged.connect(update_fields)
        update_fields()
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            proposed = {key: w.value() if key == 'baudrate' else w.currentData() for key, w in fields.items()}
            try:
                self._validated_settings(dict(analyzer=proposed))
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, 'Analyzer không hợp lệ', str(e))
                return
            self.analyzer = proposed
            self._decode_uart()

    def _snapshot_settings(self):
        return dict(analyzer=dict(self.analyzer), names=list(self.waveform.channel_names),
                    visible=list(self.waveform.channel_visible), colors=list(self.waveform.channel_colors))

    def _validated_settings(self, document):
        if not isinstance(document, dict):
            raise ValueError('Capture metadata phải là một object.')
        defaults = self._snapshot_settings()
        settings = {k: document.get(k, v) for k, v in defaults.items()}
        if (not isinstance(settings['names'], list) or len(settings['names']) != 8
                or any(not isinstance(n, str) or len(n) > 80 for n in settings['names'])):
            raise ValueError('Cần 8 tên kênh, mỗi tên tối đa 80 ký tự.')
        if not isinstance(settings['visible'], list) or len(settings['visible']) != 8 or any(type(v) is not bool for v in settings['visible']):
            raise ValueError('Trạng thái hiển thị của 8 kênh không hợp lệ.')
        if not isinstance(settings['colors'], list) or len(settings['colors']) != 8 or any(not isinstance(c, str) or not QtGui.QColor(c).isValid() for c in settings['colors']):
            raise ValueError('Màu kênh không hợp lệ.')
        a = settings['analyzer']
        if not isinstance(a, dict):
            raise ValueError('Analyzer phải là object.')
        if set(a) - set(self.analyzer):
            raise ValueError('Analyzer chứa trường cấu hình không được hỗ trợ.')
        a = {**self.analyzer, **a}
        if a['kind'] not in ('UART', 'I2C', 'SPI'):
            raise ValueError('Analyzer không hỗ trợ.')
        for key in ('channel', 'scl', 'sda', 'sck', 'mosi', 'miso', 'cs'):
            if type(a[key]) is not int or not 0 <= a[key] < 8:
                raise ValueError('Kênh giải mã phải nằm trong D0..D7.')
        if type(a['baudrate']) is not int or not 1 <= a['baudrate'] <= 3000000 or type(a['mode']) is not int or a['mode'] not in (0, 1, 2, 3) or a['bit_order'] not in ('MSB', 'LSB') or a['cs_active'] not in ('LOW', 'HIGH'):
            raise ValueError('Baudrate hoặc cấu hình SPI không hợp lệ.')
        used = [a[k] for k in ({'UART': ['channel'], 'I2C': ['scl', 'sda'], 'SPI': ['sck', 'mosi', 'miso', 'cs']}[a['kind']])]
        if len(set(used)) != len(used):
            raise ValueError('Các tín hiệu của một analyzer phải dùng các kênh khác nhau.')
        settings['analyzer'] = a
        return settings

    def _apply_channel_settings(self, settings):
        for ch in range(8):
            self.ch_edits[ch].setText(settings['names'][ch])
            self.ch_checks[ch].setChecked(settings['visible'][ch])
            self.waveform.set_channel_name(ch, settings['names'][ch])
            self.waveform.set_channel_visible(ch, settings['visible'][ch])
            self.waveform.set_channel_color(ch, settings['colors'][ch])

    def _channel_settings(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle('Channels')
        layout = QtWidgets.QGridLayout(dialog)
        names, checks, colors = [], [], list(self.waveform.channel_colors)
        for ch in range(8):
            check = QtWidgets.QCheckBox(f'D{ch}')
            check.setChecked(self.waveform.channel_visible[ch])
            name = QtWidgets.QLineEdit(self.waveform.channel_names[ch])
            name.setMaxLength(80)
            color = QtWidgets.QPushButton(colors[ch])
            def choose_color(_checked=False, channel=ch, button=color):
                picked = QtWidgets.QColorDialog.getColor(QtGui.QColor(colors[channel]), dialog)
                if picked.isValid():
                    colors[channel] = picked.name()
                    button.setText(picked.name())
            color.clicked.connect(choose_color)
            layout.addWidget(check, ch, 0)
            layout.addWidget(name, ch, 1)
            layout.addWidget(color, ch, 2)
            checks.append(check)
            names.append(name)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons, 8, 0, 1, 3)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._apply_channel_settings(dict(names=[n.text() for n in names],
                                             visible=[c.isChecked() for c in checks], colors=colors))

    def _switch_session(self, index):
        if self._busy:
            return
        previous = getattr(self, '_session_index', 0)
        if self.current_data is not None:
            self._sessions[previous] = dict(data=self.current_data, settings=self._snapshot_settings())
        if index == len(self._sessions):
            self._sessions.append(None)
            self.tab_sessions.blockSignals(True)
            self.tab_sessions.setTabText(index, f'Session {index}')
            self.tab_sessions.addTab('+')
            self.tab_sessions.blockSignals(False)
        self._session_index = index
        session = self._sessions[index]
        if session:
            self.analyzer = dict(session['settings']['analyzer'])
            self._apply_channel_settings(session['settings'])
            self._render_capture_data(session['data'])
        else:
            self.current_data = None
            self.current_uart_frames = []
            self.waveform.clear_capture()
            self.table_uart_packets.setRowCount(0)
            self.txt_uart_decoded.clear()
            self.lbl_status.setText('Session mới — Start để thu dữ liệu.')

    def _load_bin_file(self, filepath, sample_rate=1000000):
        """Use the same header/XOR validation as the real serial path."""
        if self._busy:
            return False
        res = self.client.load_offline_file(filepath, sample_rate)
        if not res.get('success'):
            self.lbl_status.setText(res['error'])
            QtWidgets.QMessageBox.warning(self, 'Tệp capture không hợp lệ', res['error'])
            return False
        self._render_capture_data(res)
        return True

    def _save_capture_file(self):
        if self._busy or not self.current_data:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save capture', 'capture.lacapture', 'Logic Capture (*.lacapture)')
        if not path:
            return
        try:
            document = dict(version=1, sample_rate=self.current_data['sample_rate'],
                            frame=capture_bytes(self.current_data).hex(), analyzer=self.analyzer,
                            names=self.waveform.channel_names, visible=self.waveform.channel_visible,
                            colors=self.waveform.channel_colors)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(document, f, ensure_ascii=False, indent=2)
            self.lbl_status.setText(f'Đã lưu capture: {path}')
        except (OSError, ValueError, KeyError) as e:
            QtWidgets.QMessageBox.warning(self, 'Không lưu được', str(e))

    def _open_capture_file(self):
        if self._busy:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open Capture', '', 'Logic Capture (*.lacapture);;Binary Capture (*.bin)')
        if not path:
            return
        if path.lower().endswith('.lacapture'):
            try:
                with open(path, encoding='utf-8') as f:
                    document = json.load(f)
                if not isinstance(document, dict) or document.get('version') != 1:
                    raise ValueError('Phiên bản capture không hỗ trợ.')
                res = parse_capture(bytes.fromhex(document['frame']), document['sample_rate'])
                settings = self._validated_settings(document)
                self.analyzer = settings['analyzer']
                self._apply_channel_settings(settings)
                self._render_capture_data(res)
            except (OSError, ValueError, KeyError, TypeError) as e:
                QtWidgets.QMessageBox.warning(self, 'Tệp capture không hợp lệ', str(e))
        else:
            labels = [r[0] for r in RATE_OPTIONS]
            label, ok = QtWidgets.QInputDialog.getItem(
                self, 'Tần số của capture', '.bin không lưu tần số. Chọn tần số đã dùng khi thu:', labels, 3, False)
            if ok:
                self._load_bin_file(path, RATE_OPTIONS[labels.index(label)][1])

    def _export_image(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Waveform Image", "waveform.png", "PNG Image (*.png);;SVG Image (*.svg)"
        )
        if path:
            ok = export_image(self.waveform.plot_widget, path)
            if ok:
                QtWidgets.QMessageBox.information(self, "Export Thành Công", f"Đã xuất ảnh đồ thị ra:\n{path}")
            else:
                QtWidgets.QMessageBox.critical(self, "Export Thất Bại", "Không thể xuất ảnh đồ thị.")

    def _export_csv(self):
        if not self.current_data:
            QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu capture để xuất CSV.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export CSV Data", "capture_data.csv", "CSV Spreadsheet (*.csv)"
        )
        if path:
            ok = export_csv(self.current_data, path)
            if ok:
                QtWidgets.QMessageBox.information(self, "Export Thành Công", f"Đã xuất dữ liệu CSV ra:\n{path}")
            else:
                QtWidgets.QMessageBox.critical(self, "Export Thất Bại", "Không thể xuất file CSV.")

    def _export_vcd(self):
        if not self.current_data:
            QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu capture để xuất VCD.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export VCD File", "capture.vcd", "Value Change Dump (*.vcd)"
        )
        if path:
            ok = export_vcd(self.current_data, path)
            if ok:
                QtWidgets.QMessageBox.information(self, "Export Thành Công", f"Đã xuất file VCD GTKWave ra:\n{path}")
            else:
                QtWidgets.QMessageBox.critical(self, "Export Thất Bại", "Không thể xuất file VCD.")
