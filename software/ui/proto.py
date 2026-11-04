"""software/ui/proto.py
Prototype GUI để đánh giá độ giống với ảnh tham chiếu (Saleae Logic 2).
Chạy: python3 -m software.ui.proto v3 out.png  hoặc  python3 software/ui/proto.py v3 out.png
"""
import os
import sys

# Khử cảnh báo Wayland requestActivate
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland=false")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

try:
    from software.ui import theme as T
except ImportError:
    import theme as T

S = 1.39            # hệ số HiDPI giả định: cửa sổ logic 1280 -> 1780 px
W, H = 1780, 1197   # kích thước ảnh tham chiếu


def px(v):
    return int(round(v * S))


# ----- Cấu hình các phiên bản --------------------------------------------------
VERSIONS = {
    # v1: đúng đúng các giá trị trong UI_SPEC.md/theme.py (đơn vị px logic)
    "v1": dict(label_w=T.LABEL_COLUMN_WIDTH, row_h=T.CHANNEL_ROW_HEIGHT, dec_scale=1.0,
               right_w=T.RIGHT_PANEL_WIDTH, rail_w=0, axis_h=26, bottom_h=34,
               menu_dark=True, font=13, strip_w=4, grid_dash=False),
    # v2: đã chỉnh theo số đo từ ảnh tham chiếu (px vật lý / 1.39)
    "v2": dict(label_w=194, row_h=47, dec_scale=1.45,
               right_w=313, rail_w=65, axis_h=32, bottom_h=42,
               menu_dark=False, font=13, strip_w=4, grid_dash=True),
}

VERSIONS["v3"] = dict(VERSIONS["v2"], stretch=True, hl=True, bit_dots=True,
                      table_marker=True, hdr_style=True, lw=1.0, card_close=True)


def uart_bits(fs=1e6, n=32768, trig=6554, text="TEST_LA_2026\r\n", baud=115200):
    y = np.ones(n, dtype=np.uint8)
    bl = fs / baud
    for i in range(trig, n):
        t = (i - trig) / bl
        f = int(t // 10)
        if f < len(text):
            pos = int(t) % 10
            if pos == 0:
                y[i] = 0
            elif pos <= 8:
                y[i] = (ord(text[f]) >> (pos - 1)) & 1
    return y


def square(n, period, duty=0.5, phase=0):
    i = (np.arange(n) + phase) % period
    return (i < period * duty).astype(np.uint8)


class TimeRulerWidget(QtWidgets.QWidget):
    """Thước đo thời gian 2 hàng chuẩn Saleae Logic 2 theo ref_comp5_time_ruler."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {T.BG_MAIN}; border: none;")

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()

        # Nền chính #1b1b1c
        painter.fillRect(0, 0, w, h, QtGui.QColor(T.BG_MAIN))

        # Viền trên và viền dưới
        painter.setPen(QtGui.QPen(QtGui.QColor(20, 20, 21), 1))
        painter.drawLine(0, 0, w, 0)
        painter.setPen(QtGui.QPen(QtGui.QColor(48, 49, 54), 1))
        painter.drawLine(0, h - 1, w, h - 1)

        ticks = [39, 157, 274, 391, 509, 743, 861, 978]
        labels_rel = ['+0.5 ms', '+0.6 ms', '+0.7 ms', '+0.8 ms', '+0.9 ms', '+0.1 ms', '+0.2 ms', '+0.3 ms']

        # Vạch subtick chỉ xuống dưới mép sóng (y: 40..43)
        painter.setPen(QtGui.QPen(QtGui.QColor(87, 87, 94), 1))
        for t in ticks:
            if t < w:
                painter.drawLine(t, 40, t, 43)

        # Hàng 1: Mốc thời gian tuyệt đối (395 ms, 396 ms)
        painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.drawText(10, 16, "395 ms")
        if 627 < w:
            painter.drawText(627, 16, "396 ms")

        # Hàng 2: Mốc thời gian tương đối (+0.5 ms, +0.6 ms...)
        painter.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
        painter.setPen(QtGui.QColor(255, 255, 255))
        for t, lbl in zip(ticks, labels_rel):
            if t < w - 25:
                painter.drawText(QtCore.QRect(t - 30, 20, 60, 16), QtCore.Qt.AlignCenter, lbl)
        painter.end()


class AnalyzersPanelWidget(QtWidgets.QWidget):
    """Component 6: Analyzers Panel (435x273 px) chuẩn Saleae Logic 2."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(273)
        self.setStyleSheet(f"background-color: {T.BG_MAIN}; border: none;")
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(20, 28, 20, 10)
        v.setSpacing(0)

        # 1. Header: Analyzers + '+'
        h = QtWidgets.QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        lbl_title = QtWidgets.QLabel("Analyzers")
        lbl_title.setStyleSheet("font-family: 'Segoe UI'; font-size: 21px; font-weight: bold; color: #ffffff; border: none;")
        h.addWidget(lbl_title)
        h.addStretch(1)

        lbl_plus = QtWidgets.QLabel("+")
        lbl_plus.setStyleSheet(f"font-family: 'Segoe UI'; font-size: 20px; color: {T.TEXT_DIM}; border: none; padding-right: 12px;")
        h.addWidget(lbl_plus)
        v.addLayout(h)

        v.addSpacing(32)

        # 2. Async Serial
        row_uart = QtWidgets.QHBoxLayout()
        row_uart.setContentsMargins(4, 0, 0, 0)
        row_uart.setSpacing(10)
        sq_uart = QtWidgets.QLabel("■")
        sq_uart.setStyleSheet("color: #d3ccb0; font-size: 14px; border: none;")
        lbl_uart = QtWidgets.QLabel("Async Serial")
        lbl_uart.setStyleSheet("font-family: 'Segoe UI'; font-size: 15px; font-weight: bold; color: #ffffff; border: none;")
        chk_uart = QtWidgets.QLabel("●")
        chk_uart.setStyleSheet(f"color: {T.ACCENT_START}; font-size: 14px; border: none;")
        row_uart.addWidget(sq_uart)
        row_uart.addWidget(lbl_uart)
        row_uart.addWidget(chk_uart)
        row_uart.addStretch(1)
        v.addLayout(row_uart)

        v.addSpacing(26)

        # 3. I2C
        row_i2c = QtWidgets.QHBoxLayout()
        row_i2c.setContentsMargins(4, 0, 0, 0)
        row_i2c.setSpacing(10)
        sq_i2c = QtWidgets.QLabel("■")
        sq_i2c.setStyleSheet("color: #4fc3e8; font-size: 14px; border: none;")
        lbl_i2c = QtWidgets.QLabel("I2C")
        lbl_i2c.setStyleSheet("font-family: 'Segoe UI'; font-size: 15px; font-weight: bold; color: #ffffff; border: none;")
        chk_i2c = QtWidgets.QLabel("●")
        chk_i2c.setStyleSheet(f"color: {T.ACCENT_START}; font-size: 14px; border: none;")
        row_i2c.addWidget(sq_i2c)
        row_i2c.addWidget(lbl_i2c)
        row_i2c.addWidget(chk_i2c)
        row_i2c.addStretch(1)
        v.addLayout(row_i2c)

        v.addSpacing(22)

        # 4. Trigger View card
        card = QtWidgets.QFrame()
        card.setFixedHeight(54)
        card.setStyleSheet(f"QFrame {{ background-color: {T.BG_CARD}; border-radius: 6px; border: 1px solid #3a3a3e; }}")
        cl = QtWidgets.QHBoxLayout(card)
        cl.setContentsMargins(14, 0, 14, 0)
        lbl_card = QtWidgets.QLabel("›  Trigger View ⚠")
        lbl_card.setStyleSheet("font-family: 'Segoe UI'; font-size: 14px; font-weight: bold; color: #ffffff; border: none; background: transparent;")
        cl.addWidget(lbl_card)
        cl.addStretch(1)
        btn_close = QtWidgets.QLabel("✕")
        btn_close.setAlignment(QtCore.Qt.AlignCenter)
        btn_close.setFixedSize(22, 22)
        btn_close.setStyleSheet(f"background-color: {T.BG_SELECT}; border-radius: 11px; color: {T.TEXT_DIM}; font-size: 11px; border: none;")
        cl.addWidget(btn_close)
        v.addWidget(card)

        v.addStretch(1)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QtGui.QPainter(self)
        p.setPen(QtGui.QPen(QtGui.QColor(87, 87, 94), 1))
        p.drawLine(0, 0, 0, self.height())
        p.end()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, P):
        super().__init__()
        self.P = P
        self.setStyleSheet(T.QSS + f"""
            QWidget {{ font-size: {px(P['font'])}px; font-family: "Segoe UI", "Inter"; }}
            QPushButton#startButton {{ border-radius: {px(25)}px; min-width: {px(50)}px;
                                       min-height: {px(50)}px; max-width: {px(50)}px; max-height: {px(50)}px; padding: 0px; }}
        """)

        # Top Bar gồm Title Bar + Menu Bar (Tổng chiều cao đúng 76 px theo ref_comp2_top_menu)
        top_container = QtWidgets.QWidget()
        top_container.setObjectName("topContainer")
        top_container.setFixedHeight(76)
        top_container.setStyleSheet("""
            QWidget#topContainer {
                background-color: #ffffff;
                color: #1b1b1c;
                border-top: 1px solid #d8d8d8;
                border-bottom: none;
            }
            QWidget {
                background-color: #ffffff;
                border: none;
            }
        """)
        top_v = QtWidgets.QVBoxLayout(top_container)
        top_v.setContentsMargins(0, 0, 0, 0)
        top_v.setSpacing(0)

        # Hàng 1: Title bar (chiều cao 40 px)
        row_title_w = QtWidgets.QWidget()
        row_title_w.setFixedHeight(40)
        row_title = QtWidgets.QHBoxLayout(row_title_w)
        row_title.setContentsMargins(14, 0, 15, 0)
        row_title.setSpacing(8)

        lbl_icon = QtWidgets.QLabel("⚙")
        lbl_icon.setStyleSheet("font-size: 16px; color: #3b82f6; border: none; background: transparent;")
        lbl_title = QtWidgets.QLabel("Logic 2 [Logic Pro 8 - Demo] [Session 1]")
        lbl_title.setStyleSheet("font-size: 12px; color: #1b1b1c; border: none; font-family: 'Segoe UI'; font-weight: normal; background: transparent;")
        row_title.addWidget(lbl_icon)
        row_title.addWidget(lbl_title)
        row_title.addStretch(1)

        for btn_txt, w_btn in (("—", 46), ("□", 46), ("✕", 48)):
            btn_w = QtWidgets.QLabel(btn_txt)
            btn_w.setFixedWidth(w_btn)
            btn_w.setAlignment(QtCore.Qt.AlignCenter)
            btn_w.setStyleSheet("font-size: 13px; color: #1b1b1c; border: none; background: transparent;")
            row_title.addWidget(btn_w)
        top_v.addWidget(row_title_w)

        # Hàng 2: Menu bar (chiều cao 36 px)
        row_menu_w = QtWidgets.QWidget()
        row_menu_w.setFixedHeight(36)
        row_menu = QtWidgets.QHBoxLayout(row_menu_w)
        row_menu.setContentsMargins(11, 4, 0, 4)
        row_menu.setSpacing(22)
        for m in ("File", "Edit", "Capture", "Measure", "View", "Help"):
            lbl_m = QtWidgets.QLabel(m)
            lbl_m.setStyleSheet("font-size: 13px; color: #1b1b1c; border: none; font-family: 'Segoe UI'; font-weight: normal; background: transparent;")
            row_menu.addWidget(lbl_m)
        row_menu.addStretch(1)
        top_v.addWidget(row_menu_w)

        self.setMenuWidget(top_container)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)
        body.addWidget(self._wave_area(), 1)
        body.addWidget(self._right_panel())
        if P["rail_w"]:
            body.addWidget(self._rail())
        outer.addWidget(self._bottom_bar())

    # ---- vùng sóng -----------------------------------------------------------
    def _wave_area(self):
        P = self.P
        row_h = px(P["row_h"])
        axis_h = 46
        if P.get("stretch"):
            avail = H - 76 - px(P["bottom_h"]) - axis_h
            row_h = int(avail / (7 + P["dec_scale"]))
        heights = [int(row_h * P["dec_scale"])] + [row_h] * 7
        total = sum(heights)
        self.row_h_used = row_h
        w = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        # cột nhãn
        lab = QtWidgets.QWidget()
        lab.setFixedWidth(px(P["label_w"]))
        lab.setStyleSheet(f"QWidget {{ background-color: {T.BG_MAIN}; border-right: 1px solid {T.GRID}; }}")
        vl = QtWidgets.QVBoxLayout(lab)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)
        top_space = QtWidgets.QWidget()
        top_space.setFixedHeight(axis_h)
        top_space.setStyleSheet(f"background-color: {T.BG_MAIN}; border-bottom: 1px solid {T.GRID};")
        vl.addWidget(top_space)
        for i, h in enumerate(heights):
            f = QtWidgets.QFrame()
            f.setFixedHeight(h)
            col = T.CHANNEL_COLORS[i]
            f.setStyleSheet(f"QFrame {{ background-color: {T.BG_MAIN}; border-left: {px(P['strip_w'])}px solid {col};"
                            f" border-bottom: 1px solid {T.BORDER}; }} QLabel {{ border: none; background: transparent; }}")
            lay = QtWidgets.QVBoxLayout(f)
            lay.setContentsMargins(px(14), px(8), 0, px(8))
            lay.setSpacing(px(4))
            top = QtWidgets.QLabel(f"<span style='color:{col};font-weight:bold;font-size:{px(11)}px'>D{i}</span>"
                                   f"&nbsp;&nbsp;&nbsp;<span style='font-size:{px(15)}px;color:#ffffff;font-family:\"Segoe UI\";'>Channel {i}</span>")
            lay.addWidget(top, 0, QtCore.Qt.AlignTop if i < 2 else QtCore.Qt.AlignVCenter)
            if i == 0:
                chip = QtWidgets.QLabel(f"<span style='color:{T.DECODE_UART_BG}'>&#9632;</span> Async Serial")
                chip.setStyleSheet(f"color:{T.TEXT_DIM};font-size:{px(11)}px;")
                lay.addWidget(chip)
                lay.addStretch(1)
            elif i == 1:
                chip = QtWidgets.QLabel(f"<span style='color:#4fc3e8'>&#9632;</span> I2C - SDA")
                chip.setStyleSheet(f"color:{T.TEXT_DIM};font-size:{px(11)}px;")
                lay.addWidget(chip)
                lay.addStretch(1)
            vl.addWidget(f)
        vl.addStretch(1)
        hl.addWidget(lab)

        # Cột sóng gồm Thước thời gian đỉnh (46px) và Khung vẽ sóng pyqtgraph
        wave_col = QtWidgets.QWidget()
        wv = QtWidgets.QVBoxLayout(wave_col)
        wv.setContentsMargins(0, 0, 0, 0)
        wv.setSpacing(0)

        ruler = TimeRulerWidget()
        ruler.setFixedHeight(axis_h)
        wv.addWidget(ruler)

        pw = pg.PlotWidget(background=T.BG_MAIN)
        pw.setFixedHeight(total)
        plot = pw.getPlotItem()
        plot.hideAxis("left"); plot.hideAxis("bottom"); plot.hideAxis("top")
        plot.hideButtons(); plot.setMenuEnabled(False)
        plot.layout.setContentsMargins(0, 0, 0, 0)
        plot.layout.setSpacing(0)
        vb = plot.getViewBox()
        vb.setMouseEnabled(False, False)
        vb.invertY(True)
        vb.setYRange(0, total, padding=0)
        vb.setXRange(-60, 640, padding=0)
        # dữ liệu
        n, trig = 32768, 6554
        sig = [uart_bits(), square(n, 10), square(n, 20), square(n, 50), square(n, 100),
               square(n, 200), square(n, 37, 0.3), square(n, 5)]
        lo_i, hi_i = trig - 80, trig + 700
        xs = np.arange(lo_i, hi_i) - trig
        y0 = 0
        hl_list = []
        grid_pen = pg.mkPen(T.GRID, width=1, style=QtCore.Qt.DashLine if P["grid_dash"] else QtCore.Qt.SolidLine)
        for gx in range(0, 700, 100):
            vb.addItem(pg.InfiniteLine(pos=gx, angle=90, pen=grid_pen))
        for i, h in enumerate(heights):
            top = y0 + (h - row_h)
            hi, lo = top + row_h * 0.22, top + row_h * 0.78
            hl_list.append((hi, lo))
            yy = np.where(sig[i][lo_i:hi_i] == 1, hi, lo)
            curve = pg.PlotCurveItem(xs, yy, stepMode="left", pen=pg.mkPen(T.CHANNEL_COLORS[i], width=P.get('lw', 1.4)))
            vb.addItem(curve)
            vb.addItem(pg.InfiniteLine(pos=y0 + h, angle=0, pen=pg.mkPen(T.BORDER)))
            y0 += h
        if P.get("hl"):
            for (hi_, lo_) in hl_list:
                for lbl, yv in (("H", hi_), ("L", lo_)):
                    t_ = pg.TextItem(lbl, color=T.TEXT, anchor=(0, 0.5))
                    t_.setPos(-57, yv); vb.addItem(t_)
        # chú thích UART
        text = "TEST_LA_2026\r\n"
        bl = 1e6 / 115200
        for k, ch in enumerate(text[:8]):
            xa, xb = k * 10 * bl + bl, (k * 10 + 9) * bl
            r = QtWidgets.QGraphicsRectItem(xa, heights[0] * 0.08, xb - xa, row_h * 0.30)
            r.setBrush(pg.mkBrush(T.DECODE_UART_BG)); r.setPen(pg.mkPen(None))
            vb.addItem(r)
            tx = pg.TextItem(f"0x{ord(ch):02X}", color=T.DECODE_UART_FG, anchor=(0.5, 0.5))
            tx.setPos((xa + xb) / 2, heights[0] * 0.08 + row_h * 0.15)
            vb.addItem(tx)
        if P.get("bit_dots"):
            hi0, lo0 = hl_list[0]
            dx, dy = [], []
            for k, ch in enumerate(text[:8]):
                for j in range(8):
                    xc = (k * 10 + 1 + j + 0.5) * bl
                    bit = (ord(ch) >> j) & 1
                    dx.append(xc); dy.append(hi0 if bit else lo0)
            sc = pg.ScatterPlotItem(dx, dy, size=px(4), brush=pg.mkBrush(T.TEXT), pen=pg.mkPen(None))
            vb.addItem(sc)
        vb.addItem(pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(T.TRIGGER_MARKER, width=2)))
        wv.addWidget(pw, 1)
        hl.addWidget(wave_col, 1)
        self.rows_total = total
        return w

    # ---- panel phải ----------------------------------------------------------
    def _right_panel(self):
        P = self.P
        w = QtWidgets.QWidget()
        w.setFixedWidth(px(P["right_w"]))
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Component 6: Analyzers Panel (435x273 px)
        ana = AnalyzersPanelWidget()
        v.addWidget(ana)

        # Phần Data Table bên dưới (Component 7)
        data_container = QtWidgets.QWidget()
        dv = QtWidgets.QVBoxLayout(data_container)
        dv.setContentsMargins(px(12), px(8), px(12), px(8))
        dv.setSpacing(px(8))

        d = QtWidgets.QLabel(f"Data &nbsp;<span style='color:{T.ACCENT_START}'>&#10004;</span>")
        d.setStyleSheet(f"font-size:{px(19)}px;font-weight:bold;")
        dv.addWidget(d)
        s = QtWidgets.QLineEdit(); s.setPlaceholderText("Type to search")
        dv.addWidget(s)
        mk = bool(P.get("table_marker"))
        nc = 4 if mk else 3
        tb = QtWidgets.QTableWidget(14, nc)
        tb.setHorizontalHeaderLabels((["", "Type", "Start", "Duration"] if mk else ["Type", "Start", "Duration"]))
        tb.verticalHeader().setVisible(False)
        tb.setAlternatingRowColors(False)
        tb.setShowGrid(False)
        tb.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for r in range(14):
            vals = ["data", f"{86.8 + r * 86.8:.1f} µs", "82.46 µs"]
            if mk:
                vals = ["■"] + vals
            for c, val in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(val)
                if mk and c == 0:
                    it.setForeground(QtGui.QBrush(QtGui.QColor(T.DECODE_UART_BG)))
                tb.setItem(r, c, it)
            tb.setRowHeight(r, px(30))
        tb.horizontalHeader().setStretchLastSection(True)
        tb.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        if mk:
            for c, wd in enumerate((28, 62, 104)):
                tb.setColumnWidth(c, px(wd))
        else:
            for c, wd in enumerate((70, 120)):
                tb.setColumnWidth(c, px(wd))
        dv.addWidget(tb, 1)

        v.addWidget(data_container, 1)
        return w

    # ---- dải icon phải -------------------------------------------------------
    def _rail(self):
        P = self.P
        w = QtWidgets.QWidget()
        w.setFixedWidth(px(P["rail_w"]))
        w.setStyleSheet(f"QWidget {{ background-color: {T.BG_MAIN}; border-left: 1px solid {T.GRID}; }}")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 1. Khoảng cách đỉnh tới nút Start (Y = 31 px)
        v.addSpacing(px(22))

        # 2. Nút Start tròn màu xanh lá (Y = 31..99 px)
        b = QtWidgets.QPushButton("▶")
        b.setObjectName("startButton")
        btn_dia = px(49)
        b.setFixedSize(btn_dia, btn_dia)
        b.setStyleSheet(f"""
            QPushButton#startButton {{
                background-color: {T.ACCENT_START};
                border: none;
                border-radius: {btn_dia // 2}px;
                color: #ffffff;
                font-size: {px(18)}px;
                padding-left: {px(2)}px;
            }}
        """)
        v.addWidget(b, 0, QtCore.Qt.AlignHCenter)

        # 3. Khoảng cách tới icon Thiết bị (Y = 160 px)
        v.addSpacing(px(34))
        btn_dev = QtWidgets.QToolButton()
        btn_dev.setText("▭")
        btn_dev.setStyleSheet(f"QToolButton {{ border: none; color: {T.TEXT_DIM}; font-size: {px(24)}px; }}")
        v.addWidget(btn_dev, 0, QtCore.Qt.AlignHCenter)

        # 4. Khoảng cách tới mục Active Analyzers (Y = 220 px)
        v.addSpacing(px(22))
        card_active = QtWidgets.QFrame()
        card_active.setFixedHeight(px(64))
        card_active.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_SELECT};
                border-left: {px(2.5)}px solid #ffffff;
                border-top: none; border-right: none; border-bottom: none;
            }}
        """)
        c_lay = QtWidgets.QVBoxLayout(card_active)
        c_lay.setContentsMargins(0, 0, 0, 0)
        btn_ana = QtWidgets.QLabel("1F")
        btn_ana.setAlignment(QtCore.Qt.AlignCenter)
        btn_ana.setStyleSheet(f"color: #ffffff; font-weight: bold; font-size: {px(16)}px; border: none; background: transparent;")
        c_lay.addWidget(btn_ana)
        v.addWidget(card_active)

        # 5. Khoảng cách tới icon Cursors / Đo đạc (Y = 369 px)
        v.addSpacing(px(32))
        btn_ruler = QtWidgets.QToolButton()
        btn_ruler.setText("📐")
        btn_ruler.setStyleSheet(f"QToolButton {{ border: none; font-size: {px(18)}px; }}")
        v.addWidget(btn_ruler, 0, QtCore.Qt.AlignHCenter)

        # 6. Khoảng cách tới icon Bố cục (Y = 476 px)
        v.addSpacing(px(46))
        btn_grid = QtWidgets.QToolButton()
        btn_grid.setText("▦")
        btn_grid.setStyleSheet(f"QToolButton {{ border: none; color: {T.TEXT_DIM}; font-size: {px(22)}px; }}")
        v.addWidget(btn_grid, 0, QtCore.Qt.AlignHCenter)

        # Đẩy 2 icon đáy xuống cuối
        v.addStretch(1)

        # 7. Icon phản hồi / Chat (Y = 952 px)
        btn_chat = QtWidgets.QToolButton()
        btn_chat.setText("💬")
        btn_chat.setStyleSheet(f"QToolButton {{ border: none; font-size: {px(18)}px; }}")
        v.addWidget(btn_chat, 0, QtCore.Qt.AlignHCenter)
        v.addSpacing(px(32))

        # 8. Icon Menu 3 gạch (Y = 1025 px)
        btn_menu = QtWidgets.QToolButton()
        btn_menu.setText("☰")
        btn_menu.setStyleSheet(f"QToolButton {{ border: none; color: {T.TEXT_DIM}; font-size: {px(22)}px; }}")
        v.addWidget(btn_menu, 0, QtCore.Qt.AlignHCenter)
        v.addSpacing(px(14))

        return w

    # ---- thanh dưới ----------------------------------------------------------
    def _bottom_bar(self):
        P = self.P
        w = QtWidgets.QWidget()
        w.setFixedHeight(px(P["bottom_h"]))
        w.setStyleSheet(f"""
            QWidget {{
                background-color: {T.BG_MAIN};
                border-top: 1px solid {T.GRID};
            }}
            QTabBar::tab {{
                background: {T.BG_MAIN};
                color: {T.TEXT_DIM};
                padding: 0px {px(16)}px;
                height: {px(P["bottom_h"]) - 1}px;
                border-top: {px(3)}px solid transparent;
                font-family: 'Segoe UI';
                font-size: {px(13)}px;
            }}
            QTabBar::tab:selected {{
                color: #ffffff;
                border-top: {px(3)}px solid #ffffff;
            }}
        """)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, px(20), 0)
        tabs = QtWidgets.QTabBar()
        tabs.setExpanding(False)
        tabs.addTab("Session 0  ✕")
        tabs.addTab("Session 1  ✕")
        tabs.addTab("+")
        tabs.setCurrentIndex(1)
        h.addWidget(tabs)
        h.addStretch(1)

        lbl_zoom = QtWidgets.QLabel("128 µs ^")
        lbl_zoom.setStyleSheet(f"color: {T.TEXT_DIM}; font-family: 'Segoe UI'; font-size: {px(13)}px; border: none; background: transparent;")
        h.addWidget(lbl_zoom)
        return w


def main():
    ver = sys.argv[1] if len(sys.argv) > 1 else "v3"
    out = sys.argv[2] if len(sys.argv) > 2 else "proto_out.png"
    app = QtWidgets.QApplication([])
    pg.setConfigOptions(antialias=False, foreground=T.TEXT)
    win = MainWindow(VERSIONS[ver])
    win.resize(W, H)
    win.show()
    for _ in range(5):
        app.processEvents()
    win.grab().save(out)
    print("row_h_used_px", getattr(win, "row_h_used", None), "ratio", getattr(win, "row_h_used", 0) / 1197)
    print("saved", out, win.size())


if __name__ == "__main__":
    main()
