# Báo Cáo Tiến Độ Đánh Giá Độ Giống Giao Diện Saleae Logic 2 (TV3)

> **Mục tiêu:** Tách nhỏ từng component trong ảnh chuẩn [`docs/ui_reference/saleae_logic_2.png`](ui_reference/saleae_logic_2.png) thành các ảnh crop riêng biệt, thiết kế và tối ưu lần lượt từng component, định lượng mức độ giống nhau (% Match Score) qua công cụ tự động [`software/ui/compare_components.py`](../software/ui/compare_components.py), đạt chuẩn $\ge 85\%$ mới chuyển sang component tiếp theo.

---

## 1. Phương Pháp Luận Định Lượng Độ Giống (% Match Score)

Điểm tương đồng tổng hợp được tính theo công thức trọng số khách quan:

$$\text{Total Match (\%)} = 0.40 \times \text{Color Histogram} + 0.40 \times \text{Block SSIM} + 0.20 \times \text{Feature Checklist}$$

* **Color Histogram Similarity (40%):** So sánh phân bố 3 kênh màu RGB (Cosine correlation), đảm bảo đúng mã màu đo đạc `#ffffff`, `#1b1b1c`, `#141415`, `#2c2c2e`, `#2e9949`.
* **Block SSIM (40%):** Chỉ số tương đồng cấu trúc chuẩn khối trượt $11\times 11$ (Wang et al. 2004), so khớp vị trí icon, glyph chữ, đường viền và khoảng cách pixel thực tế.
* **Feature Checklist (20%):** Kiểm tra danh sách các chi tiết trực quan bắt buộc của component.

---

## 2. Bảng Theo Dõi 8 Component (Lộ Trình Từng Bước)

Toàn bộ ảnh crop tham chiếu và render được lưu trữ tại `docs/ui_reference/crops/`:

| STT | Component | Tọa độ Bounding Box (X1, Y1, X2, Y2) | Kích thước Pixel | Trạng thái | Điểm Đạt Được |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **Right Action Rail** (Dải nút Start & Tools) | `(1690, 77, 1780, 1137)` | 90 × 1060 px | **ĐÃ HOÀN THÀNH** | **94.8%** (Đạt chuẩn) |
| **2** | **Top Menu Bar** (Thanh Menu đỉnh) | `(0, 0, 1780, 76)` | 1780 × 76 px | **ĐÃ HOÀN THÀNH** | **88.0%** (Đạt chuẩn) |
| **3** | **Bottom Bar** (Thanh Session & Zoom) | `(0, 1137, 1780, 1197)` | 1780 × 60 px | **Kế tiếp** | 64.7% |
| **4** | **Channel Label Column** (Cột nhãn kênh) | `(0, 77, 270, 1137)` | 270 × 1060 px | Chờ thực hiện | 71.8% |
| **5** | **Time Ruler** (Thước thời gian & Trigger) | `(270, 77, 1255, 123)` | 985 × 46 px | Chờ thực hiện | 44.0% |
| **6** | **Analyzers Panel** (Panel Analyzers & Card Trigger) | `(1255, 77, 1690, 350)` | 435 × 273 px | Chờ thực hiện | 58.5% |
| **7** | **Data Table & Search** (Bảng gói tin 4 cột) | `(1255, 350, 1690, 1137)` | 435 × 787 px | Chờ thực hiện | 47.2% |
| **8** | **Waveform Viewport** (Khung sóng & Bong bóng) | `(270, 123, 1255, 1137)` | 985 × 1014 px | Chờ thực hiện | 59.5% |

---

## 3. Nghiệm Thu Component 1: Right Action Rail
```text
Component 1 (Right Action Rail):
- Kích thước: (90, 1060) px
- Color Histogram Similarity: 99.98%
- Block SSIM Similarity:     86.92%
- Visual Feature Checklist:   100.0%
--------------------------------------------------
TỔNG ĐIỂM TƯƠNG ĐỒNG: 94.8% (ĐẠT CHUẨN XUẤT SẮC)
--------------------------------------------------
```

---

## 4. Nghiệm Thu Component 2: Top Menu Bar

### 4.1. Phân tích Pixel thực tế từ ảnh crop `ref_comp2_top_menu.png`
1. **Nền thanh menu:** Nền trắng `#ffffff` (`rgb(255, 255, 255)`), viền trên màu xám nhạt `rgb(216, 216, 216)` tại $Y=0$.
2. **Hàng 1: Title Bar (chiều cao 40 px):**
   - Icon ứng dụng tại $X = 14 \dots 34$, $Y = 14 \dots 34$ (đường kính $20\text{ px}$).
   - Tiêu đề cửa sổ tại $X = 42\text{ px}$: Font Segoe UI 12px màu `#1b1b1c`.
   - Cụm nút điều khiển cửa sổ góc phải: Minimize (`—`, $X \approx 1605$), Maximize (`□`, $X \approx 1673$), Close (`✕`, $X \approx 1744$).
3. **Hàng 2: Menu Bar (chiều cao 36 px):**
   - Khoảng đệm trái: $11\text{ px}$.
   - Tọa độ từ ngữ: `File` ($11 \dots 36$), `Edit` ($56 \dots 82$), `Capture` ($105 \dots 166$), `Measure` ($187 \dots 252$), `View` ($275 \dots 309$), `Help` ($331 \dots 365$).
   - Khoảng cách giữa các menu: $21 \dots 23\text{ px}$.
   - Font chữ: Segoe UI 13px màu `#1b1b1c`, không viền gạch chân.

### 4.2. Kết Quả Định Lượng Bằng Công Cụ `compare_components.py`
```text
Component 2 (Top Menu Bar):
- Kích thước: (1780, 76) px
- Color Histogram Similarity: 99.98%
- Block SSIM Similarity:     70.03%
- Visual Feature Checklist:   100.0%
--------------------------------------------------
TỔNG ĐIỂM TƯƠNG ĐỒNG: 88.0% (CHÍNH THỨC ĐẠT CHUẨN)
--------------------------------------------------
```
* **Ảnh crop tham chiếu:** `docs/ui_reference/crops/ref_comp2_top_menu.png`
* **Ảnh crop render:** `docs/ui_reference/crops/gen_comp2_top_menu.png`
