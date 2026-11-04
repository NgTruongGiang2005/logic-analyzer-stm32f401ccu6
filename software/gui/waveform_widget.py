#!/usr/bin/env python3
"""
software/gui/waveform_widget.py
Khung vẽ sóng logic 8 kênh (Waveform Viewport - Vùng 2):
- Hiển thị 8 kênh số (D0 - D7) xếp tầng với bảng màu Neon chuẩn thương mại trên nền tối #18181b.
- Vạch Trigger (T-Marker) đỏ đứt nét tại điểm kích hoạt, trục thời gian quy đổi t = 0 tại Trigger.
- Cặp thước đo thời gian (Cursor A & Cursor B) kéo thả trực tiếp bằng chuột.
- HUD bán trong suốt ở góc trên bên phải tự động tính toán thời gian thực:
    Δt = |t_B - t_A| | f = 1/Δt (Hz/kHz/MHz)
- Thu phóng (Zoom) lăn chuột tập trung tại con trỏ, kéo chuột trái để Pan mượt mà ở 60 FPS.
"""

from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

# Bảng màu Neon 8 kênh chuẩn chỉ định
NEON_CHANNEL_COLORS = [
    "#00f0ff",  # D0: Cyan (UART_TX)
    "#22c55e",  # D1: Emerald
    "#eab308",  # D2: Yellow
    "#f97316",  # D3: Orange
    "#a855f7",  # D4: Purple
    "#ec4899",  # D5: Pink
    "#38bdf8",  # D6: Sky Blue
    "#f43f5e",  # D7: Coral
]

DEFAULT_NAMES = [
    "D0 (UART_TX)",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
]


def format_si_time(seconds: float) -> str:
    """Định dạng thời gian theo tiền tố SI chuẩn (s, ms, µs, ns)."""
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


def format_si_freq(freq_hz: float) -> str:
    """Định dạng tần số theo tiền tố SI chuẩn (Hz, kHz, MHz)."""
    if freq_hz <= 0 or freq_hz == float("inf"):
        return "-- Hz"
    if freq_hz >= 1e6:
        return f"{freq_hz / 1e6:.3f} MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz / 1e3:.3f} kHz"
    else:
        return f"{freq_hz:.2f} Hz"


class WaveformHUD(QtWidgets.QFrame):
    """Bảng HUD bán trong suốt hiển thị thông số Cursors A & B góc trên bên phải."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 27, 0.88);
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 2px 6px;
            }
            QLabel {
                font-family: 'Consolas', 'DejaVu Sans Mono', monospace;
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(12)

        self.lbl_title = QtWidgets.QLabel("<b>CURSORS</b>")
        self.lbl_title.setStyleSheet("color: #a1a1aa;")

        self.lbl_a = QtWidgets.QLabel("A: 0.000 ms")
        self.lbl_a.setStyleSheet("color: #00f0ff;")

        self.lbl_b = QtWidgets.QLabel("B: 0.000 ms")
        self.lbl_b.setStyleSheet("color: #eab308;")

        self.lbl_dt = QtWidgets.QLabel("Δt: 0.000 µs")
        self.lbl_dt.setStyleSheet("color: #ffffff;")

        self.lbl_freq = QtWidgets.QLabel("f: -- Hz")
        self.lbl_freq.setStyleSheet("color: #22c55e;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_a)
        layout.addWidget(self.lbl_b)
        layout.addWidget(self.lbl_dt)
        layout.addWidget(self.lbl_freq)

    def update_values(self, t_a: float, t_b: float):
        self.lbl_a.setText(f"A: {format_si_time(t_a)}")
        self.lbl_b.setText(f"B: {format_si_time(t_b)}")
        dt = abs(t_b - t_a)
        self.lbl_dt.setText(f"Δt: {format_si_time(dt)}")
        if dt > 1e-12:
            self.lbl_freq.setText(f"f: {format_si_freq(1.0 / dt)}")
        else:
            self.lbl_freq.setText("f: ∞ Hz")


class WaveformWidget(QtWidgets.QWidget):
    """
    Widget đồ thị sóng 8 kênh chuyên dụng (pyqtgraph) với HUD và Cursors.
    """
    sigCursorChanged = QtCore.pyqtSignal(float, float, float)  # t_a, t_b, dt

    def __init__(self, parent=None):
        super().__init__(parent)

        self.channel_names = list(DEFAULT_NAMES)
        self.channel_visible = [True] * 8
        self.current_data: Optional[Dict[str, Any]] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. PlotWidget pyqtgraph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#18181b")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.18)
        self.plot_widget.setLabel("bottom", "Thời gian (s)", units="s")
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.setYRange(-0.4, 11.6, padding=0.01)

        # Cài đặt nhãn kênh bên trái trục Y: D0 ở trên đỉnh, D7 ở dưới đáy
        self._update_y_ticks()

        # Tạo sẵn 8 PlotCurveItem
        self.curves: List[pg.PlotCurveItem] = []
        for ch in range(8):
            pen = pg.mkPen(color=NEON_CHANNEL_COLORS[ch], width=1.8)
            curve = pg.PlotCurveItem(pen=pen)
            self.plot_widget.addItem(curve)
            self.curves.append(curve)

        # 2. Vạch chỉ thị Trigger (T-Marker) màu đỏ đứt nét
        self.trigger_line = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            pen=pg.mkPen(color="#ef4444", width=2, style=QtCore.Qt.DashLine),
            label="T (t=0)",
            labelOpts={"color": "#ef4444", "position": 0.95, "anchors": [(0, 0), (0, 0)]}
        )
        self.plot_widget.addItem(self.trigger_line)
        self.trigger_line.hide()

        # 3. Cặp Thước Đo Thời Gian (Cursors A & B)
        self.cursor_a = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            movable=True,
            pen=pg.mkPen(color="#00f0ff", width=1.8, style=QtCore.Qt.SolidLine),
            hoverPen=pg.mkPen(color="#38bdf8", width=2.5),
            label="A",
            labelOpts={"color": "#00f0ff", "position": 0.90, "anchors": [(0, 0), (0, 0)]}
        )
        self.cursor_b = pg.InfiniteLine(
            pos=0.0000868,
            angle=90,
            movable=True,
            pen=pg.mkPen(color="#eab308", width=1.8, style=QtCore.Qt.SolidLine),
            hoverPen=pg.mkPen(color="#fde047", width=2.5),
            label="B",
            labelOpts={"color": "#eab308", "position": 0.85, "anchors": [(0, 0), (0, 0)]}
        )
        self.plot_widget.addItem(self.cursor_a)
        self.plot_widget.addItem(self.cursor_b)

        self.cursor_a.sigPositionChanged.connect(self._on_cursor_moved)
        self.cursor_b.sigPositionChanged.connect(self._on_cursor_moved)

        layout.addWidget(self.plot_widget)

        # 4. Floating HUD ở góc trên bên phải
        self.hud = WaveformHUD(self)
        self.hud_widget = self.hud
        self.hud.raise_()
        self._update_hud()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Định vị HUD góc trên bên phải
        hud_w = self.hud.sizeHint().width()
        hud_h = self.hud.sizeHint().height()
        self.hud.setGeometry(self.width() - hud_w - 20, 10, hud_w, hud_h)

    def _update_y_ticks(self):
        """Cập nhật nhãn kênh trục Y tương ứng tên và màu kênh."""
        y_ticks = []
        for ch in range(8):
            y_base = (7 - ch) * 1.4 + 0.5
            name = self.channel_names[ch]
            y_ticks.append((y_base, name))
        y_axis = self.plot_widget.getAxis("left")
        y_axis.setTicks([y_ticks])
        y_axis.setWidth(110)

    def set_channel_name(self, ch: int, name: str):
        if 0 <= ch < 8:
            self.channel_names[ch] = name
            self._update_y_ticks()

    def set_channel_visible(self, ch: int, visible: bool):
        if 0 <= ch < 8:
            self.channel_visible[ch] = visible
            self.curves[ch].setVisible(visible)

    def toggle_cursors(self, visible: Optional[bool] = None):
        """Bật / tắt hiển thị cặp thước đo A & B và HUD."""
        if visible is None:
            visible = not self.cursor_a.isVisible()
        self.cursor_a.setVisible(visible)
        self.cursor_b.setVisible(visible)
        self.hud.setVisible(visible)

    def _on_cursor_moved(self):
        self._update_hud()

    def _update_hud(self):
        t_a = self.cursor_a.value()
        t_b = self.cursor_b.value()
        dt = abs(t_b - t_a)
        self.cursor_a.label.setText(f"A: {format_si_time(t_a)}")
        self.cursor_b.label.setText(f"B: {format_si_time(t_b)}")
        self.hud.update_values(t_a, t_b)
        self.sigCursorChanged.emit(t_a, t_b, dt)

    def set_cursor_positions(self, t_a: float, t_b: float):
        self.cursor_a.setValue(t_a)
        self.cursor_b.setValue(t_b)
        self._update_hud()

    def set_positions(self, t_a: float, t_b: float):
        self.set_cursor_positions(t_a, t_b)

    def get_cursor_values(self) -> Tuple[float, float, float]:
        t_a = self.cursor_a.value()
        t_b = self.cursor_b.value()
        return t_a, t_b, abs(t_b - t_a)

    def get_delta_t(self) -> float:
        _, _, dt = self.get_cursor_values()
        return dt

    def get_frequency(self) -> float:
        dt = self.get_delta_t()
        return (1.0 / dt) if dt > 1e-12 else 0.0

    def render_data(self, res: Dict[str, Any]):
        """
        Vẽ 8 kênh dữ liệu lên viewport với mốc thời gian t = 0 tại Trigger.
        """
        self.current_data = res
        channels = res["channels"]
        sample_rate = float(res["sample_rate"])
        sample_count = int(res["sample_count"])
        trig_offset = int(res["trig_offset"])
        status = res.get("status", 0)

        # 1. Trục thời gian quy đổi t = 0 tại Trigger nếu Trigger thành công
        if status == 0:  # STATUS_TRIGGER_OK
            time_axis = (np.arange(sample_count + 1, dtype=np.float64) - trig_offset) / sample_rate
            t_marker = 0.0
            self.trigger_line.setValue(t_marker)
            self.trigger_line.setPen(pg.mkPen(color="#ef4444", width=2, style=QtCore.Qt.DashLine))
            self.trigger_line.label.setText("T (t=0)")
            self.trigger_line.show()
            x_min = -trig_offset / sample_rate
            x_max = (sample_count - trig_offset) / sample_rate
        elif status == 1:  # STATUS_FREERUN_OK
            time_axis = np.arange(sample_count + 1, dtype=np.float64) / sample_rate
            t_marker = trig_offset / sample_rate
            self.trigger_line.setValue(t_marker)
            self.trigger_line.setPen(pg.mkPen(color="#71717a", width=1.5, style=QtCore.Qt.DotLine))
            self.trigger_line.label.setText("MỐC 20% (FREE-RUN)")
            self.trigger_line.show()
            x_min = 0.0
            x_max = sample_count / sample_rate
        else:  # STATUS_TIMEOUT
            time_axis = np.arange(sample_count + 1, dtype=np.float64) / sample_rate
            t_marker = trig_offset / sample_rate
            self.trigger_line.setValue(t_marker)
            self.trigger_line.setPen(pg.mkPen(color="#f97316", width=1.8, style=QtCore.Qt.DashDotLine))
            self.trigger_line.label.setText("TIMEOUT")
            self.trigger_line.show()
            x_min = 0.0
            x_max = sample_count / sample_rate

        # 2. Vẽ 8 đường sóng phân tầng
        for ch in range(8):
            ch_data = channels[ch].astype(np.float32)
            y_base = (7 - ch) * 1.4
            y_data = ch_data + y_base
            self.curves[ch].setData(x=time_axis, y=y_data, stepMode="center")
            self.curves[ch].setVisible(self.channel_visible[ch])

        # 3. Đặt thước đo A và B gần điểm bắt sóng
        if status == 0:
            self.set_cursor_positions(0.0, 8.68e-5)
        else:
            self.set_cursor_positions(t_marker, t_marker + 8.68e-5)

        # 4. Zoom Fit toàn cảnh
        self.plot_widget.setXRange(x_min, x_max, padding=0.01)

    def zoom_fit(self):
        """Khôi phục góc nhìn toàn bộ dữ liệu mẫu."""
        if not self.current_data:
            return
        sample_count = int(self.current_data["sample_count"])
        sample_rate = float(self.current_data["sample_rate"])
        trig_offset = int(self.current_data["trig_offset"])
        status = self.current_data.get("status", 0)

        if status == 0:
            x_min = -trig_offset / sample_rate
            x_max = (sample_count - trig_offset) / sample_rate
        else:
            x_min = 0.0
            x_max = sample_count / sample_rate
        self.plot_widget.setXRange(x_min, x_max, padding=0.01)

    def zoom_to_window(self, t_start_abs: float, t_stop_abs: float):
        """Phóng to và căn giữa một khoảng thời gian xác định."""
        if not self.current_data:
            return
        status = self.current_data.get("status", 0)
        sample_rate = float(self.current_data["sample_rate"])
        trig_offset = int(self.current_data["trig_offset"])

        if status == 0:
            offset_s = trig_offset / sample_rate
            t1 = t_start_abs - offset_s
            t2 = t_stop_abs - offset_s
        else:
            t1 = t_start_abs
            t2 = t_stop_abs

        dur = max(t2 - t1, 0.00004)
        self.plot_widget.setXRange(t1 - dur * 0.4, t2 + dur * 0.4, padding=0)
