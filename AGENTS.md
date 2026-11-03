# AGENTS.md: Hướng Dẫn & Quy Chuẩn Hoạt Động Cho AI Agent

Tài liệu này xác định các nguyên tắc ứng xử, quy chuẩn kỹ thuật, ràng buộc phần cứng/phần mềm và quy trình kiểm thử bắt buộc đối với mọi AI Coding Agent (Antigravity, Claude Code, Cursor, Copilot, v.v.) khi tham gia phát triển trong repository **`Embedded_System`** (Đề tài 1: Logic Analyzer 8 kênh 6 MHz - STM32F401CCU6).

---

## 1. Triết Lý & Nguyên Tắc Cốt Lõi (Karpathy Guidelines)

Mọi thay đổi mã nguồn do Agent thực hiện phải tuân thủ nghiêm ngặt 4 nguyên tắc sau:

### 1.1. Suy nghĩ trước khi lập trình (Think Before Coding)
* **Làm rõ giả định:** Xác định rõ ràng các giả định trước khi sửa code. Nếu có điểm mơ hồ hoặc thiếu dữ liệu, phải dừng lại và hỏi người dùng, không được tự suy diễn.
* **Đánh giá đánh đổi (Trade-offs):** Nếu có nhiều phương án kỹ thuật, hãy trình bày ngắn gọn ưu/nhược điểm thay vì âm thầm chọn một cách.
* **Tôn trọng giải pháp đơn giản:** Đề xuất phương án tối giản nhất đáp ứng đề bài; chủ động phản biện nếu yêu cầu có dấu hiệu over-engineering.

### 1.2. Đơn giản là trên hết (Simplicity First)
* **Tối thiểu hóa mã nguồn:** Chỉ viết lượng code vừa đủ để giải quyết bài toán hiện tại.
* **Không suy đoán tính năng:** Không viết sẵn các hàm trừu tượng (abstract layer), helper, wrapper cho các tính năng chưa được yêu cầu.
* **Không bắt lỗi viển vông:** Tránh bọc `try-catch` hoặc kiểm tra điều kiện cho các trường hợp bất khả thi về mặt vật lý/toán học.
* **Tự vấn:** *"Một senior embedded engineer có thấy đoạn code này rườm rà không?"* Nếu có, hãy viết lại ngắn hơn.

### 1.3. Chỉnh sửa chính xác như phẫu thuật (Surgical Changes)
* **Chỉ chạm vào chỗ cần thiết:** Không tự ý format lại code, chỉnh sửa comment cũ, hoặc "dọn dẹp" các hàm lân cận không liên quan đến yêu cầu.
* **Hòa nhập phong cách:** Tuân thủ phong cách lập trình (naming convention, thụt lề, cấu trúc) sẵn có của file đang sửa.
* **Dọn sạch rác phát sinh:** Nếu thay đổi làm thừa import, biến hoặc hàm nội bộ, phải xóa chúng ngay. Tuyệt đối không xóa dead code cũ của project nếu không được yêu cầu.

### 1.4. Thực thi theo mục tiêu và kiểm chứng (Goal-Driven Execution)
* Mọi hành động phải có tiêu chí nghiệm thu rõ ràng:
  * Thêm logic $\rightarrow$ Viết kiểm thử / kịch bản xác nhận $\rightarrow$ Chạy thử thành công.
  * Sửa lỗi $\rightarrow$ Tái hiện lỗi $\rightarrow$ Áp dụng bản vá $\rightarrow$ Kiểm tra lỗi biến mất.
* Luôn tuân theo chu trình: `[Kế hoạch ngắn gọn]` $\rightarrow$ `[Thực thi]` $\rightarrow$ `[Kiểm tra lại]`.

---

## 2. Nguồn Chân Lý Duy Nhất (Single Source of Truth - SSoT)

Mọi Agent phải tôn trọng thứ bậc ưu tiên tài liệu:
1. [**`spec/protocol.md`**](spec/protocol.md): Quy định tuyệt đối về định dạng khung truyền, checksum, mã lệnh, mã trạng thái, và timing giao tiếp giữa STM32 và PC GUI.
2. [**`spec/logic_analyzer_specification.md`**](spec/logic_analyzer_specification.md): Đặc tả kiến trúc phần cứng, ánh xạ ngoại vi STM32, bảng ARR/tần số lấy mẫu, tính toán bảo vệ đầu vào.
3. [**`spec/Logic_analyzer_requirements.md`**](spec/Logic_analyzer_requirements.md): Đề bài gốc của môn học (HUST 2026.1).
4. [**`docs/`**](docs/): Datasheet STM32F401, RM0368 Reference Manual, sơ đồ nguyên lý WeAct Black Pill V3.0.

> [!CAUTION]
> **Tuyệt đối không tự ý thay đổi định dạng gói tin, mã lệnh hoặc công thức tính trong `spec/protocol.md`** trừ khi có chỉ đạo rõ ràng từ người dùng.

---

## 3. Ràng Buộc Kỹ Thuật Theo Từng Phân Hệ

### 3.1. Phân hệ Firmware (`firmware/`)
1. **Quy tắc STM32CubeMX (Sống còn):**
   * Các file do CubeMX sinh ra (`main.c`, `stm32f4xx_it.c`, `usbd_cdc_if.c`, v.v.) **CHỈ ĐƯỢC CHỈNH SỬA TRONG VÙNG `/* USER CODE BEGIN ... */` VÀ `/* USER CODE END ... */`**.
   * Mọi logic nghiệp vụ phải được bọc trong các module độc lập:
     * `Core/Inc/la_core.h`, `Core/Src/la_core.c` (FSM, Timer, DMA, Trigger)
     * `Core/Inc/la_protocol.h`, `Core/Src/la_protocol.c` (Phân tích lệnh & đóng gói dữ liệu)
     * `Core/Inc/la_testgen.h`, `Core/Src/la_testgen.c` (Tạo tín hiệu test UART PA9)
2. **Quản trị Bộ nhớ SRAM (64 KB):**
   * Buffer bắt tín hiệu: Mảng tĩnh `la_sample_buffer[32768]` (chiếm đúng 32 KB = 50% SRAM).
   * **Cấm dùng cấp phát động (`malloc`, `free`)**: Mọi biến, bộ đệm phải được khai báo tĩnh (`static`) hoặc cấp phát trên stack trong giới hạn.
3. **Phối hợp Ngoại vi & Ngắt:**
   * **Lấy mẫu:** `TIM1` Update TRGO $\rightarrow$ kích hoạt `DMA2_Stream5 Channel 6` đọc từ `GPIOA->IDR` (PA0–PA7) vào circular buffer 32KB.
   * **Bộ đếm Post-trigger:** `TIM2` Slave mode ITR0 (nối với `TIM1_TRGO`), One-Pulse Mode, ngắt `TIM2_IRQHandler` dừng hệ thống khi đếm đủ $26.213$ mẫu (80%).
   * **Chống rỗng Pre-trigger (Bắt buộc):** Chỉ kích hoạt ngắt trigger EXTI sau khi cờ DMA Half-Transfer (`HTIF5`) được bật (đã ghi ít nhất 16.384 mẫu = 50% buffer).
   * **Xung đột PA9:** PA9 được dùng làm USART1_TX phát xung test. Phải tắt tính năng `VBUS sensing` của USB OTG_FS trong CubeMX để giải phóng PA9.
4. **Định dạng dữ liệu:**
   * Các trường số nguyên 16-bit truyền qua USB (`trig_offset = 6554`, `sample_count = 32768`) **phải theo thứ tự Little-Endian** (`0x9A, 0x19` và `0x00, 0x80`).

---

### 3.2. Phân hệ Phần cứng & Mô phỏng (`hardware/`)
1. **Giới hạn chịu đựng tuyệt đối của STM32F401:**
   * Điện áp cấp và điện áp trên chân I/O tối đa: **$V_{DD\_\text{max}} = 4.0\text{ V}$**.
   * Mạch kẹp diode bảo vệ đầu vào (rail 3.3V hoặc diode Zener/TL431) phải đảm bảo điện áp tại chân MCU không vượt quá $3.6\text{ V} - 3.8\text{ V}$ trong mọi trường hợp.
2. **Trường hợp xấu nhất cần mô phỏng (LTspice):**
   * Xung quá áp **$200\text{ V} / 1\text{ ms}$** cấp vào 1 kênh: dòng xả đỉnh qua trở đầu vào $1\text{ k}\Omega$ là $I_{\text{peak}} \approx 196\text{ mA}$.
   * Phải mô phỏng với **model có trở động ($r_d \approx 10-20\,\Omega$)**, không dùng model Zener lý tưởng.
   * Trở đầu vào $R_1$ phải là loại chịu xung công suất (pulse-withstanding), không dùng trở film SMD thông thường kích thước nhỏ.
3. **Đặc thù phần cứng Kit Black Pill V3.0:**
   * Chân **PA0** nối với nút nhấn KEY qua trở nối tiếp $R = 330\,\Omega$ xuống GND (không có tụ dập nhiễu). Tín hiệu đo 6 MHz vẫn qua bình thường nếu không bấm nút.
   * Chân **PC13** nối LED trạng thái (tích cực mức thấp).

---

### 3.3. Phân hệ Phần mềm PC & Giao diện (`software/`)
1. **Quy tắc phân giải khung truyền (GUI Frame Dispatcher):**
   * Khi nhận dữ liệu từ Serial, GUI **phải đọc trước 7 bytes Header** và kiểm tra `Byte 2`:
     * Nếu `Byte 2` $\in [0x00, 0x01, 0x02]$: Đây là **Data Frame** $\rightarrow$ đọc tiếp đúng $32.769\text{ Bytes}$ còn lại (tổng gói là $32.776\text{ Bytes}$).
     * Nếu `Byte 2` $\in [0x04, 0x05, 0xE0..0xE3]$: Đây là **Control / NAK Frame** $\rightarrow$ dừng lại ở $7\text{ Bytes}$, xử lý trạng thái ngay.
2. **Cơ chế khóa giao diện khi đang truyền (State Locking):**
   * Khi gửi lệnh `START`, GUI rơi vào trạng thái chờ nhận dữ liệu. Tuyệt đối **không gửi thêm bất kỳ lệnh nào** (Ping, Abort) làm nghẽn hoặc hỏng luồng truyền 32KB.
3. **Ngân sách thời gian chờ (Timeout Budget):**
   * GUI Timeout phải luôn lớn hơn MCU Timeout ít nhất $1.5\text{ s}$:
     $$T_{\text{gui-timeout}} \ge \left(\frac{16384}{f_s} + 2.0\text{ s}\right) + 1.5\text{ s}$$
4. **Kiểm thử độc lập không cần kit:**
   * Trước khi test trên phần cứng thật, module GUI và Decoder phải chạy pass với `software/tests/mock_serial.py` và `software/tests/sample_data_1mhz.bin`.

---

## 4. Quy Chuẩn Git & Làm Việc Nhóm

### 4.1. Quy ước Phân nhánh (Branching Convention)
* **`main`**: Nhánh chính, chỉ chứa mã nguồn đã kiểm thử và hoạt động ổn định.
* Các nhánh chức năng bắt buộc đặt tiền tố:
  * `fw/*`: Các tính năng hoặc bản sửa lỗi của Firmware (TV1).
  * `hw/*`: Bản vẽ mạch, mô phỏng LTspice, BOM (TV2).
  * `sw/*`: Giao diện GUI, Decoder, Unit test (TV3).
  * `docs/*`: Cập nhật tài liệu, đặc tả, slide, báo cáo.
* Hợp nhất vào `main` thông qua Pull Request (PR).

### 4.2. Quy ước Commit Message (Conventional Commits)
Sử dụng cấu trúc chuẩn:
```text
<type>(<scope>): <mô tả ngắn gọn bằng tiếng Anh hoặc tiếng Việt>
```
* **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
* **Scopes:** `firmware`, `hardware`, `software`, `spec`, `protocol`.
* **Ví dụ:**
  * `feat(firmware): add TIM2 one-pulse post-trigger handler`
  * `fix(protocol): correct little-endian trig_offset bytes`
  * `test(software): add mock serial runner for timeout verification`

### 4.3. Quản lý Tài nguyên Nhị phân
* **Quy tắc Single Owner cho file văn phòng:**
  * Slide tiến độ (`report/slides_11_11/`): TV1 quản lý.
  * Báo cáo Word cuối kỳ (`report/final_report/`): TV2 quản lý.
* **Cấm commit video:** File video demo (`.mp4`, `.mkv`) lưu trên Cloud (Teams/Drive), chỉ lưu đường dẫn trong `report/demo/README.md`.
* **File `.gitignore`:** Không được phép xóa ngoại lệ của `!software/tests/*.bin` và `!firmware/STM32F401_STLink.launch`.

---

## 5. Quy Trình Kiểm Tra Bắt Buộc (Verification Checklist)

Trước khi Agent thông báo hoàn thành bất kỳ nhiệm vụ nào, hãy thực hiện kiểm tra tương ứng:

| Phân hệ | Hành động | Lệnh / Cách kiểm tra | Tiêu chuẩn Đạt |
| :--- | :--- | :--- | :--- |
| **All** | Trạng thái Git | `git status` | Không có file rác, file nhị phân không mong muốn. |
| **Firmware** | Vùng User Code | Rà soát `main.c`, `usbd_cdc_if.c` | Không có dòng code nào nằm ngoài `USER CODE BEGIN/END`. |
| **Firmware** | Định dạng số | `grep -rn "0x9A" firmware/` | Khớp Little-Endian với `spec/protocol.md`. |
| **Software** | Sinh mẫu & Mock | `python software/tests/generate_test_data.py` | Tạo thành công `sample_data_1mhz.bin` (32.776 bytes). |
| **Software** | Kiểm tra cú pháp | `python -m py_compile software/**/*.py` | Không có lỗi syntax Python. |
| **Tài liệu** | Công thức KaTeX | Rà soát file `.md` trong `spec/` | Không có ký tự `_` tự do trong math block (phải dùng `T_{\text{mcu-timeout}}`). |

---

*Tài liệu này được áp dụng tức thì cho mọi Agent và thành viên dự án.*
