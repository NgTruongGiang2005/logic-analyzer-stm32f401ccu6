# UI_SPEC.md: Đặc Tả Giao Diện Người Dùng Chuẩn Thương Mại (HUST Logic Analyzer)

> **Tài liệu tham chiếu chuẩn cho phân hệ phần mềm Desktop (TV3 - Desktop Application Developer)**  
> **Dự án:** Thiết bị phân tích logic 8 kênh 6 MHz trên STM32F401CCU6 (WeAct Black Pill V3.0)  
> **Ảnh tham chiếu thiết kế nội bộ:** [`docs/ui_reference/saleae_logic_2.png`](docs/ui_reference/saleae_logic_2.png)  
> **Nhận diện thương hiệu dự án:** **HUST Logic Analyzer** (Không dùng nhãn hiệu thương mại Saleae / Logic 2).

---

## 1. Bố Cục Tổng Thể (Overall Window Layout)

Giao diện ứng dụng được chia thành **3 vùng chức năng chính** và **2 thanh công cụ neo biên** (Top Menu Bar và Bottom Session/Status Bar):

```
+-----------------------------------------------------------------------------------------------+
| Top Menu Bar: File | Capture | View | Decoders | Help                                         |
+-----------------------------------------------------------------------------+-----------------+
|                                                                             | Right Action    |
| [VÙNG 1: WAVEFORM VIEWPORT (~70% bề ngang)]                                 | Dock (~48px):   |
| +-------------------------------------------------------------------------+ | [▶ Start]       |
| | Time Ruler: Hàng trên (395 ms, 396 ms...) | Hàng dưới (+0.5 ms, +1.0 ms)| | (Nút tròn xanh) |
| +-------------------------------------------------------------------------+ |                 |
| | D0 [UART_TX]  |--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_-- | | [Devices]       |
| | D1 [SCL]      |--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_-- | | [Analyzers]     |
| | D2 [SDA]      |--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_--_-- | | [Cursors]       |
| | D3..D7        |                                                         | | [Export]        |
| |               | [T-Marker t=0]   | Cursor A |          | Cursor B |     | |                 |
| +---------------+---------------------------------------------------------+ | [Settings]      |
+-----------------------------------------------------------------------------+                 |
| [VÙNG 2: RIGHT SIDEBAR (~30% bề ngang, QSplitter kéo giãn)]                 |                 |
| - Panel Analyzers: Danh sách bộ giải mã đang kích hoạt (UART, I2C, SPI)      |                 |
| - Panel Data / Terminal: Bảng gói tin giải mã (Type, Start, Duration, Data)  |                 |
+-----------------------------------------------------------------------------+-----------------+
| Bottom Status Bar: Port | Sample Rate | Samples (32,768) | Status: IDLE | Zoom: 128 µs        |
+-----------------------------------------------------------------------------------------------+
```

---

## 2. Bảng Màu Thực Đo Chuẩn Xác (Measured Pixel Palette)

Toàn bộ mã màu dưới đây được trích xuất trực tiếp từ mẫu pixel của ảnh tham chiếu [`docs/ui_reference/saleae_logic_2.png`](docs/ui_reference/saleae_logic_2.png):

### 2.1. Màu Hệ Thống & Nền Tảng (Core System Colors)
| Thành phần giao diện | Mã Hex thực đo | Vai trò & Ứng dụng |
| :--- | :--- | :--- |
| **Nền chính (Main Background)** | `#1b1b1c` | Nền khung sóng Viewport (chiếm ~70% diện tích cửa sổ) |
| **Nền vùng sâu (Deep Background)** | `#141415` | Nền hàng bảng gói tin, nền sidebar, vùng lùi cấp |
| **Thẻ & Ô nhập (Card / Input)** | `#2c2c2e` | Top control bar, ô nhập baudrate, dropdown combobox |
| **Mục Sidebar đang chọn (Active)** | `#3a3a3e` | Tab đang chọn, icon dock đang kích hoạt, hover |
| **Đường viền ranh giới (Border)** | `#3a3a3c` | Đường phân chia panel, viền ô nhập, đường kẻ bảng |
| **Nút Start (Action Primary)** | `#2e9949` | Nút kích hoạt lấy mẫu (xanh lá công nghiệp, hover `#35ac53`) |
| **Nút Abort (Action Danger)** | `#e11d48` | Nút dừng khẩn cấp (đỏ tươi công nghiệp, hover `#f43f5e`) |
| **Chữ chính (Text Primary)** | `#ffffff` | Tiêu đề, số liệu đo, nhãn nút bấm, giá trị hex |
| **Chữ phụ (Text Secondary / Muted)**| `#a0a0a2` | Nhãn cổng COM, đơn vị đo, thông số phụ |
| **Vạch chỉ thị Trigger (T-Marker)** | `#f66c7e` | Nét đứt màu đỏ nhạt tại mẫu danh định 6554 ($t = 0$) |

### 2.2. Bảng Màu 8 Kênh Đo Số (8-Channel Digital Trace Palette)
| Kênh | Nhãn mặc định | Mã Hex thực đo | Tên màu công nghiệp | Độ tương phản trên `#1b1b1c` |
| :--- | :--- | :--- | :--- | :--- |
| **D0** | `D0 (UART_TX)` | `#d4d4d4` | Silver White | 11.2:1 (Rõ nét tuyệt đối) |
| **D1** | `D1 (I2C_SCL)` | `#c39577` | Warm Copper | 7.8:1 (Dịu mắt, chuẩn WCAG AAA) |
| **D2** | `D2 (I2C_SDA)` | `#f66c7e` | Salmon Coral | 7.6:1 (Chuẩn WCAG AAA) |
| **D3** | `D3 (SPI_MOSI)`| `#f9b353` | Amber Orange | 9.4:1 (Chuẩn WCAG AAA) |
| **D4** | `D4 (SPI_MISO)`| `#e6d71a` | Lemon Yellow | 13.8:1 (Rực rỡ, dễ nhận biết) |
| **D5** | `D5 (SPI_SCK)` | `#67c662` | Fresh Green | 8.9:1 (Chuẩn WCAG AAA) |
| **D6** | `D6 (CH6)`     | `#4ea8de` | Sky Blue | 9.2:1 (Tương phản cao) |
| **D7** | `D7 (CH7)`     | `#b388ff` | Lavender Violet | 8.5:1 (Tương phản cao) |

### 2.3. Chú Thích Giải Mã Giao Thức (In-line Protocol Bubbles)
* **UART (Async Serial):** Bubble chữ nhật bo góc $R = 3\text{px}$ màu vàng nhạt `#fde047` chứa chữ đậm `#1c1917` (ví dụ `0x54 'T'`). Từng bit được đánh dấu bằng chấm nhỏ màu trắng đục.
* **I2C Bus:**
  - START: Chấm tròn màu xanh lá (`#22c55e`).
  - Address / Data: Bubble màu xanh dương (`#38bdf8`) chứa text `#0f172a` (ví dụ `W[0x3C]`, `0xAA`).
  - ACK / STOP: Ô vuông màu cam (`#f97316`).
* **SPI Bus:** Bubble màu tím nhạt (`#c084fc`) chứa text `#1e1b4b` cho luồng MOSI / MISO song công.

---

## 3. Quy Chuẩn Kỹ Thuật Các Thành Phần

### 3.1. Thước Thời Gian (Time Ruler)
* Đặt cố định ở đỉnh của vùng xem sóng (Waveform Viewport).
* **2 tầng hiển thị thời gian:**
  - Hàng trên: Thời gian tuyệt đối tính từ đầu bộ đệm (ví dụ `0.000 ms`, `6.554 ms`, `32.768 ms`).
  - Hàng dưới: Thời gian tương đối quy chiếu lấy $t=0$ tại điểm kích hoạt Trigger danh định mẫu 6554 (ví dụ `-6.554 ms`, `0.000 ms`, `+26.214 ms`).
* Lưới dọc nét đứt (Vertical gridlines) màu `#2c2c2e` chạy thẳng xuyên suốt từ thước đo xuống qua toàn bộ 8 hàng kênh.

### 3.2. Hàng Kênh Đo (Channel Trace Rows)
* Mỗi kênh chiếm một hàng riêng biệt, xếp tầng từ D0 (trên cùng) đến D7 (dưới cùng).
* **Cột nhãn kênh (Left Channel Header):**
  - Chiếm khoảng 1/6 bề rộng khung sóng.
  - Mã kênh (`D0`, `D1`...) in đậm theo đúng màu của kênh đó.
  - Tên kênh (người dùng có thể sửa trực tiếp hoặc đổi nhãn).
  - Chip/Badge nhỏ hiển thị giao thức đang gán (ví dụ: `Async Serial` nền `#2c2c2e` chữ `#fde047`).
  - Mép trái hiển thị hai mức logic `H` (High = 3.3V) và `L` (Low = 0V).
* **Đường sóng logic:** Nét vẽ 1.5px theo đúng màu kênh, chuyển mức thẳng đứng dứt khoát không có overshoot.

### 3.3. Cặp Thước Đo Thời Gian (Dual Timing Cursors A & B)
* Hai đường thẳng đứng có thể kéo thả tự do bằng chuột trên đồ thị:
  - Cursor A: Màu Cyan (`#00f0ff` / `#4ea8de`).
  - Cursor B: Màu Vàng chanh (`#f9b353` / `#e6d71a`).
* **Khung HUD đo đạc tự động:** Nằm bán trong suốt (`rgba(27, 27, 28, 220)`) tại góc trên bên phải khung sóng, cập nhật thời gian thực khi rê chuột:
  $$\Delta t = |t_B - t_A| \quad (\mu\text{s}, \text{ms}) \qquad f = \frac{1}{\Delta t} \quad (\text{Hz}, \text{kHz}, \text{MHz})$$

### 3.4. Bảng Kết Quả Giải Mã (Decoded Data Table)
* Đặt trong tab `Protocol Decoders` ở sidebar bên phải.
* **4 cột chuẩn mực:**
  - `#`: Số thứ tự gói tin (căn giữa, rộng 45px).
  - `Time (ms)`: Thời điểm bắt đầu của ký tự/frame (căn phải, rộng 95px).
  - `Decoded`: Ký tự ASCII hoặc loại gói (`START`, `ADDR`, `STOP`) (căn giữa, rộng 90px).
  - `Hex Data`: Giá trị byte nhị phân dạng hex `0xXX` (căn giữa/trái, giãn đầy đủ bề ngang).
* **Tính năng Click-to-Jump:** Click vào bất kỳ hàng nào trong bảng, đồ thị sóng lập tức tự động Pan và Zoom mượt mà tới đúng khung thời gian của gói tin đó.

---

## 4. Quy Chuẩn Kiểu Chữ (Typography)

* **Font hệ thống chính (UI Labels, Buttons, Menus):** `'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif`.
  - Cỡ chữ nhãn thông thường: `11px` - `12px`, font-weight `400` / `500`.
  - Cỡ chữ tiêu đề bảng, nhóm: `12px`, font-weight `bold`.
* **Font dữ liệu kỹ thuật & thời gian (Monospace):** `'Consolas', 'JetBrains Mono', 'DejaVu Sans Mono', monospace`.
  - Dùng cho bảng Data Table, Terminal giải mã, nhãn thời gian, tọa độ Cursor A/B và giá trị Hex.

---

## 5. Quy Chuẩn Tách Biệt Theme Thành Module Code

Mọi định nghĩa màu sắc và stylesheet được tập trung duy nhất tại module [**`software/gui/theme.py`**](software/gui/theme.py):
* Các file giao diện (`main_window.py`, `waveform_widget.py`, `cursors.py`) **tuyệt đối không hardcode màu sắc** mà phải import trực tiếp từ `software.gui.theme`.
* Khi cần tinh chỉnh màu sắc cho toàn bộ ứng dụng, chỉ sửa duy nhất tại `software/gui/theme.py`.
