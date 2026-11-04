# Báo Cáo Tiến Độ Đánh Giá Độ Giống Giao Diện Saleae Logic 2 (TV3)

> **Mục tiêu:** Tách nhỏ từng component trong ảnh chuẩn [`docs/ui_reference/saleae_logic_2.png`](ui_reference/saleae_logic_2.png) thành các ảnh crop riêng biệt, thiết kế và tối ưu lần lượt từng component, định lượng mức độ giống nhau (% Match Score) qua công cụ tự động [`software/ui/compare_components.py`](../software/ui/compare_components.py), đạt chuẩn $\ge 85\%$ mới chuyển sang component tiếp theo.

---

## 1. Phương Pháp Luận Định Lượng Độ Giống (% Match Score)

Điểm tương đồng tổng hợp được tính theo công thức trọng số khách quan:

$$\text{Total Match (\%)} = 0.40 \times \text{Color Histogram} + 0.40 \times \text{SSIM} + 0.20 \times \text{Feature Checklist}$$

* **Color Histogram Similarity (40%):** So sánh phân bố 3 kênh màu RGB (Cosine correlation), đảm bảo đúng mã màu đo đạc `#1b1b1c`, `#141415`, `#2c2c2e`, `#2e9949`.
* **SSIM - Structural Similarity (40%):** So sánh tương quan cấu trúc hình học, vị trí icon, vạch phân cách, độ dày viền và kích thước pixel thực tế.
* **Feature Checklist (20%):** Kiểm tra danh sách các chi tiết trực quan bắt buộc của component (icon, viền active, font, căn lề).

---

## 2. Bảng Theo Dõi 8 Component (Lộ Trình Từng Bước)

Toàn bộ ảnh crop tham chiếu và render được lưu trữ tại `docs/ui_reference/crops/`:

| STT | Component | Tọa độ Bounding Box (X1, Y1, X2, Y2) | Kích thước Pixel | Trạng thái | Điểm Đạt Được |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **Right Action Rail** (Dải nút Start & Tools) | `(1690, 77, 1780, 1137)` | 90 × 1060 px | **ĐÃ HOÀN THÀNH** | **85.4%** (Đạt chuẩn) |
| **2** | **Top Menu Bar** (Thanh Menu đỉnh) | `(0, 0, 1780, 76)` | 1780 × 76 px | Kế tiếp | 39.2% |
| **3** | **Bottom Bar** (Thanh Session & Zoom) | `(0, 1137, 1780, 1197)` | 1780 × 60 px | Chờ thực hiện | 64.7% |
| **4** | **Channel Label Column** (Cột nhãn kênh) | `(0, 77, 270, 1137)` | 270 × 1060 px | Chờ thực hiện | 71.8% |
| **5** | **Time Ruler** (Thước thời gian & Trigger) | `(270, 77, 1255, 123)` | 985 × 46 px | Chờ thực hiện | 44.0% |
| **6** | **Analyzers Panel** (Panel Analyzers & Card Trigger) | `(1255, 77, 1690, 350)` | 435 × 273 px | Chờ thực hiện | 58.5% |
| **7** | **Data Table & Search** (Bảng gói tin 4 cột) | `(1255, 350, 1690, 1137)` | 435 × 787 px | Chờ thực hiện | 47.2% |
| **8** | **Waveform Viewport** (Khung sóng & Bong bóng) | `(270, 123, 1255, 1137)` | 985 × 1014 px | Chờ thực hiện | 59.5% |

---

## 3. Nghiệm Thu Component 1: Right Action Rail

### 3.1. Phân tích Pixel thực tế từ ảnh crop `ref_comp1_right_rail.png`
1. **Nút Start xanh lá:**
   - Tâm tọa độ: $X = 45$, $Y = 65$ (sai số $\le 0.5\text{ px}$).
   - Đường kính: $68 \times 68\text{ px}$ (chuẩn logic $50\text{ px} \times 1.39$).
   - Màu sắc: `#2e9949` (`rgb(46, 153, 73)`), tam giác trắng `▶` ở tâm.
2. **Icon Device (Thiết bị):** Vị trí $Y \approx 160$, biểu tượng hình chữ nhật bo góc viền mảnh (`▭`).
3. **Mục Active (Analyzers):**
   - Vị trí: $Y = 220 \dots 309$ (chiều cao $89\text{ px}$).
   - Nền sáng hơn: `#3a3a3e` (`rgb(58, 58, 62)`).
   - Vạch trắng kích hoạt bên mép trái: $X = 1 \dots 3$, dài suốt chiều cao mục active (`#ffffff`, rộng $3\text{ px}$).
   - Icon trung tâm: Huy hiệu vuông `1F`.
4. **Icon Đo đạc (Measure / Cursors):** Vị trí $Y \approx 369$, biểu tượng thước tam giác góc 45 độ (`📐`).
5. **Icon Bố cục (Layout):** Vị trí $Y \approx 476$, biểu tượng lưới 4 ô chữ nhật (`▦`).
6. **Cụm icon đáy (Bottom dock):**
   - Icon phản hồi: $Y \approx 952$, bong bóng chat (`💬`).
   - Icon menu hệ thống: $Y \approx 1025$, 3 vạch ngang (`☰`).

### 3.2. Kết Quả Định Lượng Bằng Công Cụ `compare_components.py`
```
Component 1 (Right Action Rail):
- Kích thước so khớp: (90, 1060) vs (90, 1060) px
- Color Histogram Similarity: 99.98%
- Structural Similarity (SSIM): 63.62%
- Visual Feature Checklist: 100.0%
==================================================
TỔNG ĐIỂM TƯƠNG ĐỒNG: 85.4% (ĐẠT CHUẨN ĐẦU TIÊN)
==================================================
```
* **Ảnh crop tham chiếu:** `docs/ui_reference/crops/ref_comp1_right_rail.png`
* **Ảnh crop render:** `docs/ui_reference/crops/gen_comp1_right_rail.png`
