#!/usr/bin/env python3
"""
software/gui/cursors.py
Quản lý cặp thước đo thời gian (Cursor A & Cursor B) kéo thả trực tiếp trên đồ thị pyqtgraph.
Tự động tính toán mốc thời gian t_A, t_B, khoảng cách Δt và tần số tương ứng f = 1/Δt (HUD).
"""

from typing import Optional, Callable, Tuple
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg


def format_time(seconds: float) -> str:
    """Định dạng thời gian với tiền tố SI chuẩn (s, ms, µs, ns)."""
    abs_s = abs(seconds)
    sign = "-" if seconds < 0 else ""
    if abs_s >= 1.0:
        return f"{sign}{abs_s:.4f} s"
    elif abs_s >= 1e-3:
        return f"{sign}{abs_s * 1e3:.3f} ms"
    elif abs_s >= 1e-6:
        return f"{sign}{abs_s * 1e6:.3f} µs"
    else:
        return f"{sign}{abs_s * 1e9:.1f} ns"


def format_freq(freq_hz: float) -> str:
    """Định dạng tần số với tiền tố SI chuẩn (Hz, kHz, MHz)."""
    if freq_hz <= 0 or freq_hz == float("inf"):
        return "-- Hz"
    if freq_hz >= 1e6:
        return f"{freq_hz / 1e6:.3f} MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz / 1e3:.3f} kHz"
    else:
        return f"{freq_hz:.2f} Hz"


class CursorHUDWidget(QtWidgets.QFrame):
    """Bảng hiển thị thông số thời gian HUD của Cặp Thước Đo A & B."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 0.85);
                border: 1px solid #444;
                border-radius: 6px;
                padding: 2px 6px;
            }
            QLabel {
                font-family: 'Consolas', 'DejaVu Sans Mono', monospace;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(14)

        self.lbl_a = QtWidgets.QLabel("A: 0.000 ms")
        self.lbl_a.setStyleSheet("color: #00e5ff; background: transparent;")

        self.lbl_b = QtWidgets.QLabel("B: 0.000 ms")
        self.lbl_b.setStyleSheet("color: #ffb74d; background: transparent;")

        self.lbl_dt = QtWidgets.QLabel("Δt: 0.000 µs")
        self.lbl_dt.setStyleSheet("color: #ffffff; background: transparent;")

        self.lbl_freq = QtWidgets.QLabel("f: -- Hz")
        self.lbl_freq.setStyleSheet("color: #69f0ae; background: transparent;")

        layout.addWidget(QtWidgets.QLabel("<b>CURSORS:</b>"))
        layout.addWidget(self.lbl_a)
        layout.addWidget(self.lbl_b)
        layout.addWidget(self.lbl_dt)
        layout.addWidget(self.lbl_freq)

    def update_hud(self, t_a: float, t_b: float):
        """Cập nhật các chỉ số thời gian lên HUD."""
        self.lbl_a.setText(f"A: {format_time(t_a)}")
        self.lbl_b.setText(f"B: {format_time(t_b)}")

        dt = abs(t_b - t_a)
        self.lbl_dt.setText(f"Δt: {format_time(dt)}")

        if dt > 1e-12:
            freq = 1.0 / dt
            self.lbl_freq.setText(f"f: {format_freq(freq)}")
        else:
            self.lbl_freq.setText("f: ∞ Hz")


class CursorManager(QtCore.QObject):
    """
    Quản lý 2 đường thước đo dọc Cursor A & Cursor B trên pyqtgraph PlotWidget.
    """
    sigCursorsChanged = QtCore.pyqtSignal(float, float, float)  # t_a, t_b, dt

    def __init__(self, plot_widget: pg.PlotWidget, hud_widget: Optional[CursorHUDWidget] = None):
        super().__init__()
        self.plot_widget = plot_widget
        self.hud_widget = hud_widget

        # 1. Khởi tạo Thước Đo A (Cyan)
        self.cursor_a = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            movable=True,
            pen=pg.mkPen(color="#00e5ff", width=1.8, style=QtCore.Qt.SolidLine),
            hoverPen=pg.mkPen(color="#00ffff", width=2.5),
            label="A",
            labelOpts={"color": "#00e5ff", "position": 0.95, "anchors": [(0, 0), (0, 0)]}
        )

        # 2. Khởi tạo Thước Đo B (Amber / Orange)
        self.cursor_b = pg.InfiniteLine(
            pos=0.001,
            angle=90,
            movable=True,
            pen=pg.mkPen(color="#ffb74d", width=1.8, style=QtCore.Qt.SolidLine),
            hoverPen=pg.mkPen(color="#ffa726", width=2.5),
            label="B",
            labelOpts={"color": "#ffb74d", "position": 0.90, "anchors": [(0, 0), (0, 0)]}
        )

        self.plot_widget.addItem(self.cursor_a)
        self.plot_widget.addItem(self.cursor_b)

        # Kết nối sự kiện kéo thước
        self.cursor_a.sigPositionChanged.connect(self._on_cursor_moved)
        self.cursor_b.sigPositionChanged.connect(self._on_cursor_moved)

        self._visible = True
        self._update_all()

    def set_visible(self, visible: bool):
        """Bật / tắt hiển thị thước đo và HUD."""
        self._visible = visible
        if visible:
            self.cursor_a.show()
            self.cursor_b.show()
            if self.hud_widget:
                self.hud_widget.show()
        else:
            self.cursor_a.hide()
            self.cursor_b.hide()
            if self.hud_widget:
                self.hud_widget.hide()

    def is_visible(self) -> bool:
        return self._visible

    def set_positions(self, t_a: float, t_b: float):
        """Thiết lập vị trí hai thước đo."""
        self.cursor_a.setValue(t_a)
        self.cursor_b.setValue(t_b)
        self._update_all()

    def get_positions(self) -> Tuple[float, float]:
        """Lấy vị trí hiện tại (t_a, t_b)."""
        return self.cursor_a.value(), self.cursor_b.value()

    def get_delta_t(self) -> float:
        """Lấy khoảng cách thời gian Δt."""
        t_a, t_b = self.get_positions()
        return abs(t_b - t_a)

    def get_frequency(self) -> float:
        """Lấy tần số f = 1/Δt."""
        dt = self.get_delta_t()
        return (1.0 / dt) if dt > 1e-12 else 0.0

    def _on_cursor_moved(self):
        """Callback khi người dùng kéo chuột di chuyển một trong hai thước."""
        self._update_all()

    def _update_all(self):
        t_a, t_b = self.get_positions()
        dt = abs(t_b - t_a)

        # Cập nhật nhãn trên thước
        self.cursor_a.label.setText(f"A: {format_time(t_a)}")
        self.cursor_b.label.setText(f"B: {format_time(t_b)}")

        # Cập nhật HUD widget
        if self.hud_widget:
            self.hud_widget.update_hud(t_a, t_b)

        # Phát tín hiệu Qt
        self.sigCursorsChanged.emit(t_a, t_b, dt)
