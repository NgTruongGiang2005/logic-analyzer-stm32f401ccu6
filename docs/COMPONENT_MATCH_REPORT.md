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
| **3** | **Bottom Bar** (Thanh Session & Zoom) | `(0, 1137, 1780, 1197)` | 1780 × 60 px | **ĐÃ HOÀN THÀNH** | **89.4%** (Đạt chuẩn) |
| **4** | **Channel Label Column** (Cột nhãn kênh) | `(0, 77, 270, 1137)` | 270 × 1060 px | **Kế tiếp** | 71.8% |
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

---

## 5. Nghiệm Thu Component 3: Bottom Bar

### 5.1. Phân tích Pixel thực tế từ ảnh crop `ref_comp3_bottom_bar.png`
1. **Viền trên đáy:** Vạch ngang phân cách $1\text{ px}$ màu `#57575e` (`rgb(87, 87, 94)`) tại $Y=0$.
2. **Dải tab Session bên trái:**
   - Tab 0 (`Session 0  ✕`): Inactive, chữ `#a0a0a6`, viền trên trong suốt.
   - Tab 1 (`Session 1  ✕`): Active, chữ trắng `#ffffff`, **vạch chỉ thị trắng dày $3\text{ px}$ nằm ở mép trên tab** ($Y = 2 \dots 4$, $X = 157 \dots 308$).
   - Tab 2 (`+`): Nút tạo phiên mới, căn giữa.
3. **Mức thu phóng (Zoom Level) góc phải:**
   - Tọa độ: $X = 1680 \dots 1753$, $Y = 24 \dots 40$ (căn lề phải cách biên $20\text{ px}$).
   - Nội dung: `128 µs ^` màu `#a0a0a6` Font Segoe UI 13px.

### 5.2. Kết Quả Định Lượng Bằng Công Cụ `compare_components.py`
```text
Component 3 (Bottom Bar):
- Kích thước: (1780, 60) px
- Color Histogram Similarity: 99.98%
- Block SSIM Similarity:     73.61%
- Visual Feature Checklist:   100.0%
--------------------------------------------------
TỔNG ĐIỂM TƯƠNG ĐỒNG: 89.4% (CHÍNH THỨC ĐẠT CHUẨN)
--------------------------------------------------
```
* **Ảnh crop tham chiếu:** `docs/ui_reference/crops/ref_comp3_bottom_bar.png`
* **Ảnh crop render:** `docs/ui_reference/crops/gen_comp3_bottom_bar.png`
