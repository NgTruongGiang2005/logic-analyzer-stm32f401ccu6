# AGENTS.md: Hướng Dẫn & Quy Chuẩn Hoạt Động Cho AI Agent (Dành cho TV1 - Firmware)

Tài liệu này xác định các nguyên tắc ứng xử, quy chuẩn kỹ thuật, ràng buộc phần cứng và quy trình kiểm thử bắt buộc đối với AI Coding Agent khi hỗ trợ **TV1 (Kỹ sư Firmware)** phát triển mã nguồn nhúng trong repository **`Embedded_System`** (Đề tài 1: Logic Analyzer 8 kênh 6 MHz - STM32F401CCU6).

---

## 1. Triết Lý & Nguyên Tắc Cốt Lõi (Karpathy Guidelines)

Mọi thay đổi mã nguồn do Agent thực hiện phải tuân thủ nghiêm ngặt 4 nguyên tắc sau:

### 1.1. Suy nghĩ trước khi lập trình (Think Before Coding)
* **Làm rõ giả định ngoại vi:** Xác định rõ cơ chế ngắt, pipeline DMA, quan hệ timer master/slave, và clock tree trước khi sửa code. Nếu có điểm mơ hồ, dừng lại và hỏi người dùng.
* **Đánh giá đánh đổi (Trade-offs):** Khi xử lý ngắt và thời gian thực (real-time constraints), hãy nêu rõ ưu/nhược điểm (ví dụ: cờ ngắt vs polling, ISR gọn nhẹ vs callback).
* **Tôn trọng giải pháp đơn giản:** Viết mã tối giản, trực tiếp vào thanh ghi hoặc HAL theo quy chuẩn, không tạo thêm tầng abstraction không cần thiết.

### 1.2. Đơn giản là trên hết (Simplicity First)
* **Tối thiểu hóa mã nguồn:** Chỉ viết lượng code vừa đủ để hoàn thành tính năng firmware được yêu cầu.
* **Không suy đoán tính năng:** Không viết sẵn các hàm helper, wrapper hoặc cấu trúc dữ liệu cho các tính năng chưa có trong spec.
* **Không bắt lỗi viển vông:** Tránh bọc kiểm tra cho các trường hợp bất khả thi về mặt vật lý của thanh ghi MCU.
* **Tự vấn:** *"Một senior embedded engineer có thấy đoạn code này rườm rà không?"* Nếu có, hãy viết lại ngắn gọn hơn.

### 1.3. Chỉnh sửa chính xác như phẫu thuật (Surgical Changes)
* **Chỉ chạm vào chỗ cần thiết:** Không tự ý format lại code, chỉnh sửa comment có sẵn, hoặc xáo trộn cấu trúc file CubeMX sinh ra.
* **Quy tắc CubeMX sống còn:** Tuyệt đối chỉ viết code trong các vùng `/* USER CODE BEGIN ... */` và `/* USER CODE END ... */`.
* **Dọn sạch rác phát sinh:** Nếu sửa đổi làm thừa biến, macro, include trong module của mình, phải dọn sạch ngay. Không xóa dead code cũ của thư viện ST HAL.

### 1.4. Thực thi theo mục tiêu và kiểm chứng (Goal-Driven Execution)
* Mọi thay đổi firmware phải có tiêu chí nghiệm thu rõ ràng:
  * Thêm logic FSM / Driver $\rightarrow$ Kiểm tra biên dịch không lỗi/cảnh báo $\rightarrow$ Kiểm tra cờ thanh ghi / USB packet.
  * Sửa lỗi timing/trigger $\rightarrow$ Tái hiện nguyên nhân $\rightarrow$ Áp dụng bản vá $\rightarrow$ Xác nhận trạng thái FSM.
* Luôn tuân theo chu trình: `[Kế hoạch ngắn gọn]` $\rightarrow$ `[Thực thi]` $\rightarrow$ `[Kiểm tra lại]`.

---

## 2. Nguồn Chân Lý Duy Nhất (Single Source of Truth - SSoT)

Mọi quyết định thiết kế firmware phải tuân theo thứ bậc tài liệu sau:
1. [**`spec/protocol.md`**](spec/protocol.md): Quy định tuyệt đối về định dạng khung truyền, checksum, mã lệnh (5B), khung phản hồi/NAK (7B), khung dữ liệu (32.776B), và timing USB-CDC.
2. [**`spec/logic_analyzer_specification.md`**](spec/logic_analyzer_specification.md): Đặc tả kiến trúc Timer/DMA, bảng ARR/tần số lấy mẫu, ánh xạ chân GPIO, và cấu hình xung nhịp (Clock tree).
3. [**`spec/Logic_analyzer_requirements.md`**](spec/Logic_analyzer_requirements.md): Đề bài gốc của môn học (HUST 2026.1).
4. [**`docs/`**](docs/): Datasheet STM32F401, RM0368 Reference Manual, sơ đồ nguyên lý WeAct Black Pill V3.0.

> [!CAUTION]
> **Tuyệt đối không tự ý thay đổi định dạng gói tin, mã lệnh hoặc công thức tính trong `spec/protocol.md`** trừ khi có chỉ đạo rõ ràng từ TV1.

---

## 3. Ràng Buộc Kỹ Thuật Cốt Lõi Cho Firmware (`firmware/`)

### 3.1. Cấu trúc Module & Bảo vệ STM32CubeMX
* Các file do CubeMX sinh ra (`main.c`, `stm32f4xx_it.c`, `usbd_cdc_if.c`, v.v.) **CHỈ ĐƯỢC CHỈNH SỬA TRONG VÙNG `/* USER CODE BEGIN ... */` VÀ `/* USER CODE END ... */`**.
* Toàn bộ mã nguồn nghiệp vụ phải được bọc trong các module độc lập:
  * `Core/Inc/la_core.h`, `Core/Src/la_core.c`: FSM hệ thống, khởi động/dừng Timer, DMA, cấu hình ngắt Trigger, timeout.
  * `Core/Inc/la_protocol.h`, `Core/Src/la_protocol.c`: Bộ giải mã sliding window cho lệnh 5 bytes, đóng gói khung phản hồi 7 bytes và data frame 32.776 bytes.
  * `Core/Inc/la_testgen.h`, `Core/Src/la_testgen.c`: Module phát tín hiệu mẫu UART 115200 bps trên PA9 phục vụ tự test loopback.

### 3.2. Quản trị Bộ nhớ SRAM (Giới hạn 64 KB của STM32F401CCU6)
* Buffer bắt tín hiệu: Mảng tĩnh `la_sample_buffer[32768]` (chiếm đúng 32 KB = 50% SRAM).
* **Cấm dùng cấp phát động (`malloc`, `free`)**: Mọi buffer và biến trạng thái phải được khai báo tĩnh (`static`) hoặc cấp phát trên stack trong giới hạn an toàn.

### 3.3. Phối hợp Ngoại vi & Timing
1. **Lấy mẫu (Sampling):**
   * Xung nhịp: SYSCLK = 84 MHz, APB1/APB2 Timer clocks = 84 MHz.
   * `TIM1` Update TRGO $\rightarrow$ kích hoạt `DMA2_Stream5 Channel 6` đọc từ `GPIOA->IDR` (PA0–PA7) vào `la_sample_buffer` (chế độ Circular).
2. **Bộ đếm Post-trigger:**
   * `TIM2` Slave mode ITR0 (nối với `TIM1_TRGO`), External Clock Mode 1, One-Pulse Mode (`ARR = 26213`).
   * Ngắt `TIM2_IRQHandler` dừng hệ thống khi đếm đủ $26.214$ xung (tương ứng 80% bộ đệm sau trigger).
3. **Chống rỗng Pre-trigger (Bắt buộc):**
   * Tuyệt đối không bật ngắt trigger EXTI ngay khi nhận lệnh START.
   * Chỉ kích hoạt ngắt trigger EXTI sau khi cờ DMA Half-Transfer (`HTIF5`) được bật (đã ghi ít nhất 16.384 mẫu = 50% buffer), đảm bảo luôn có đủ $\ge 20\%$ pre-trigger data.
4. **Xoay vòng bộ đệm (Buffer Unrolling):**
   * Do DMA2 ghi vòng Circular, khi dừng lấy mẫu, vị trí con trỏ `write_pos = 32768 - DMA2_Stream5->NDTR` là vị trí của mẫu cũ nhất ($t_0$).
   * Firmware phải gửi dữ liệu xoay vòng từ `write_pos` đến cuối mảng rồi tiếp tục từ đầu mảng đến `write_pos - 1`, đảm bảo điểm trigger luôn khớp đúng mốc `trig_offset = 6554` và dữ liệu liên tục theo thời gian (kể cả khi Timeout).
5. **Xung đột PA9 (Sống còn):**
   * Chân PA9 được dùng làm `USART1_TX` phát xung test.
   * Phải **tắt tính năng `VBUS sensing` của USB OTG_FS** trong CubeMX để giải phóng chân PA9, tránh xung đột phần cứng.
6. **Chân Debug & Ngoại vi phụ:**
   * **PC13**: LED trạng thái trên kit Black Pill V3.0 (Active Low: kéo xuống 0 là sáng).
   * **PA0**: Chân nối với nút KEY qua trở $330\,\Omega$ xuống GND (không có tụ). Cần lưu ý không nhấn nút trong lúc lấy mẫu.

### 3.4. Định dạng Dữ liệu & Giao thức USB-CDC
* **Little-Endian:** Các trường 16-bit gửi qua USB phải luôn theo thứ tự Little-Endian:
  * `trig_offset = 6554` $\rightarrow$ bytes `0x9A, 0x19`.
  * `sample_count = 32768` $\rightarrow$ bytes `0x00, 0x80`.
* **Trạng thái Truyền (`TRANSFERRING`):**
  * Trong lúc đang đẩy 32.776 bytes qua USB, MCU **bỏ qua hoàn toàn mọi byte nhận được từ cổng USB** để tránh hỏng khung dữ liệu.
* **Timeout động:**
  $$T_{\text{mcu-timeout}} = \frac{16384}{f_s} + 2.0\text{ s}$$
  Được định thời bằng biến đếm mili-giây trong `SysTick_Handler()`. Khi hết timeout mà chưa có trigger, MCU tự động dừng lấy mẫu và gửi 32.776 bytes với Status `0x02` (`STATUS_TIMEOUT`).

---

## 4. Quy Chuẩn Git Dành Cho TV1

### 4.1. Quy ước Phân nhánh (Branching)
* Không commit code dở dang trực tiếp lên `main`.
* TV1 làm việc trên các nhánh có tiền tố `fw/`:
  * `fw/setup-cubemx`
  * `fw/tim-dma-capture`
  * `fw/cdc-protocol`
  * `fw/test-loopback`
* Tạo Pull Request (PR) merge vào `main` sau khi kiểm tra biên dịch và test chức năng đạt chuẩn.

### 4.2. Quy ước Commit Message
Tuân thủ Conventional Commits:
```text
<type>(firmware): <mô tả ngắn gọn công việc>
```
* **Ví dụ:**
  * `feat(firmware): configure TIM1 TRGO and DMA2 stream5 circular capture`
  * `feat(firmware): add TIM2 post-trigger one-pulse handler`
  * `fix(firmware): correct little-endian trig_offset in protocol frame`
  * `chore(firmware): update .ioc clock tree to 84MHz`

### 4.3. Quản lý File & Build Artifacts
* **Cấm commit file build rác:** Không commit các file `.o`, `.d`, `.elf`, `.bin`, `.hex`, `.map` hoặc thư mục `Debug/`, `Release/`.
* **File cấu hình ST-Link:** File cấu hình debug `firmware/STM32F401_STLink.launch` đã được miễn trừ trong `.gitignore`, cần được giữ nguyên để cả nhóm dùng chung cấu hình nạp.

---

## 5. Quy Trình Kiểm Tra Bắt Buộc Trước Khi Commit (Checklist)

| Mục kiểm tra | Cách thực hiện | Tiêu chuẩn Đạt |
| :--- | :--- | :--- |
| **Vùng User Code** | Rà soát `main.c`, `stm32f4xx_it.c`, `usbd_cdc_if.c` | 100% code tùy biến nằm trong `/* USER CODE BEGIN ... */` và `/* USER CODE END ... */`. |
| **Biên dịch** | Build trong STM32CubeIDE (`Ctrl+B`) hoặc Make/CMake | `0 errors, 0 warnings`. |
| **Định dạng số** | `grep -rn "0x9A" firmware/` | Khớp Little-Endian `0x9A, 0x19` với `spec/protocol.md`. |
| **Quản trị bộ nhớ** | Kiểm tra file `.map` sau khi build | Dung lượng SRAM sử dụng không vượt quá 64 KB (buffer 32 KB chiếm đúng 50%). |
| **Trạng thái Git** | Chạy `git status` | Không có file nhị phân rác hoặc file tạm của IDE bị thêm vào git. |

---

*Tài liệu này là quy chuẩn hoạt động bắt buộc cho mọi tương tác hỗ trợ TV1 phát triển Firmware.*
