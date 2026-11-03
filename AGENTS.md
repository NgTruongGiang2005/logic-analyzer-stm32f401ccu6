# AGENTS.md: Hướng Dẫn & Quy Chuẩn Hoạt Động Cho AI Agent (Dành riêng cho TV1 - Firmware STM32)

Tài liệu này xác định các nguyên tắc ứng xử, quy chuẩn kỹ thuật, ràng buộc phần cứng, phong cách mã nguồn và quy trình kiểm thử bắt buộc đối với AI Coding Agent khi hỗ trợ **TV1 (Kỹ sư Firmware)** phát triển mã nguồn nhúng trong repository **`Embedded_System`** (Đề tài 1: Logic Analyzer 8 kênh 6 MHz - STM32F401CCU6).

---

## 1. Bối Cảnh Dự Án & Giới Hạn Phần Cứng

* **Mục tiêu:** Xây dựng thiết bị Logic Analyzer 8 kênh thu thập đồng bộ với tần số lấy mẫu lên tới 6 MHz.
* **Vi điều khiển (MCU):** **STM32F401CCU6** (WeAct Black Pill V3.0) — **SRAM 64 KB** (TUYỆT ĐỐI KHÔNG PHẢI 96 KB), Flash 256 KB.
* **Clock Tree:** 
  * Thạch anh ngoài (HSE): $25\text{ MHz}$.
  * Cấu hình PLL: $M=25, N=336, P=4, Q=7 \implies$ **SYSCLK = 84 MHz**, **APB1/APB2 Timer Clock = 84 MHz**, **USB OTG_FS = 48 MHz**.
* **Ánh xạ Kênh vào & Xung đột Chân:**
  * Kênh đo 0 – 7: Nối vào **PA0 – PA7** (đọc trực tiếp thanh ghi `GPIOA->IDR`).
  * PA0 nối với nút KEY qua trở $330\,\Omega$ xuống GND (không có tụ dập nhiễu; lưu ý không nhấn nút khi đang đo).
  * Chân **PA9** dùng làm `USART1_TX` phát xung kiểm thử loopback $\implies$ **BẮT BUỘC PHẢI TẮT TÍNH NĂNG `VBUS sensing` của USB OTG_FS** trong CubeMX để giải phóng chân PA9.
  * Chân **PC13**: LED trạng thái trên kit (Active Low: kéo xuống mức 0 là bật sáng).

---

## 2. Nguồn Chân Lý Duy Nhất (Single Source of Truth - SSoT)

Khi phát sinh mâu thuẫn kỹ thuật, Agent phải tuân thủ nghiêm ngặt thứ bậc ưu tiên sau:
1. [**`spec/protocol.md`**](spec/protocol.md): Quy định tuyệt đối về định dạng khung truyền byte-level, mã lệnh (5B), mã phản hồi/NAK (7B), gói dữ liệu (32.776B) và timeout USB-CDC.
2. [**`spec/logic_analyzer_specification.md`**](spec/logic_analyzer_specification.md): Đặc tả kiến trúc Timer/DMA, bảng ARR, cấu hình clock và FSM lấy mẫu.
3. **ST RM0368 Reference Manual & Datasheet STM32F401**: Căn cứ duy nhất về hành vi thanh ghi, thứ tự xóa cờ ngắt và pipeline DMA. Không tự suy đoán hành vi phần cứng.
4. **Comment trong mã nguồn hiện có**.

---

## 3. Phạm Vi File Được Phép & Bị Cấm Chỉnh Sửa

### 3.1. Các file ĐƯỢC PHÉP tạo và chỉnh sửa:
* Toàn bộ mã nguồn nghiệp vụ độc lập:
  * `firmware/Core/Inc/la_core.h`, `firmware/Core/Src/la_core.c` (FSM, Timer, DMA, Trigger)
  * `firmware/Core/Inc/la_protocol.h`, `firmware/Core/Src/la_protocol.c` (Phân tích lệnh & đóng gói USB)
  * `firmware/Core/Inc/la_testgen.h`, `firmware/Core/Src/la_testgen.c` (Bộ phát xung UART mẫu PA9)
* Các file do CubeMX sinh ra (`main.c`, `stm32f4xx_it.c`, `usbd_cdc_if.c`): **CHỈ ĐƯỢC CHÈN LỜI GỌI HOOK TRONG CÁC KHỐI `/* USER CODE BEGIN ... */` VÀ `/* USER CODE END ... */`**.

### 3.2. Các file và thư mục TUYỆT ĐỐI CẤM tự ý sửa đổi:
* `Drivers/`, `Middlewares/`, `Core/Startup/startup_stm32f401ccux.s`, `STM32F401CCUX_FLASH.ld`.
* File cấu hình `firmware/*.ioc`.
* Các thư mục ngoài phân hệ firmware: `hardware/`, `software/`, `spec/` (trừ khi có chỉ đạo rõ ràng từ TV1).

### 3.3. Quy trình khi cần thay đổi cấu hình ngoại vi (CubeMX):
* Agent **KHÔNG ĐƯỢC TỰ Ý SỬA** các file khởi tạo ngoại vi do CubeMX quản lý.
* Agent phải **hướng dẫn từng bước thao tác trong CubeMX GUI cho người dùng** (chọn peripheral nào, tick thông số gì).
* **Checklist kiểm tra lại sau khi người dùng bấm Generate Code:**
  1. Tính năng *VBUS sensing* của OTG_FS có bị CubeMX tự ý bật lại không? (Nếu có $\rightarrow$ phải tắt lại).
  2. Bảng ưu tiên ngắt NVIC có bị xáo trộn không?
  3. Code tự viết trong các vùng `/* USER CODE BEGIN ... */` có còn nguyên vẹn không?

---

## 4. Kiến Trúc Firmware & Ràng Buộc Ngoại Vi Đã Chốt

Agent tuyệt đối không tự ý thay đổi cấu trúc phần cứng đã chốt:

1. **Lấy mẫu tín hiệu (Sampling Engine):**
   * `TIM1` Update TRGO $\rightarrow$ kích hoạt `DMA2_Stream5 Channel 6` đọc từ `GPIOA->IDR` (PA0–PA7) vào mảng tĩnh `la_capture_buffer[32768]` ở chế độ Circular.
   * **Bảng ARR chuẩn của TIM1 (PSC = 0, Clock = 84 MHz):**
     * `13` (6 MHz), `27` (3 MHz), `41` (2 MHz), `83` (1 MHz), `167` (500 kHz), `419` (200 kHz), `839` (100 kHz), `1679` (50 kHz), `8399` (10 kHz).
2. **Bộ đếm Post-trigger (Hardware Counter):**
   * `TIM2` Slave mode ITR0 (nối nội bộ với `TIM1_TRGO`), External Clock Mode 1, One-Pulse Mode.
   * Cài đặt `ARR = 26213` để đếm chính xác $26.214\text{ mẫu}$ (80% bộ đệm sau trigger). Ngắt tràn `TIM2_IRQHandler` dừng tức thì `TIM1`.
3. **Phân cấp Ưu tiên Ngắt NVIC Cố định:**
   * **Priority 0 (Cao nhất):** `EXTI0_IRQHandler` đến `EXTI9_5_IRQHandler` (Cạnh Trigger - đòi hỏi độ trễ tối thiểu).
   * **Priority 1:** `TIM2_IRQHandler` (Dừng lấy mẫu khi đủ $26.214$ mẫu).
   * **Priority 2:** `OTG_FS_IRQHandler` (Truyền thông USB-CDC).
4. **Máy trạng thái FSM (State Machine):**
   $$\text{IDLE} \longrightarrow \text{ARMED} \longrightarrow \text{PRE\_SAMPLING} \longrightarrow \text{WAIT\_TRIGGER} \longrightarrow \text{POST\_SAMPLING} \longrightarrow \text{TRANSFERRING} \longrightarrow \text{IDLE}$$
   * **Chống rỗng Pre-trigger (Bắt buộc):** Ở `PRE_SAMPLING`, cấm unmask EXTI ngay. Chỉ chuyển sang `WAIT_TRIGGER` và mở EXTI sau khi cờ DMA Half-Transfer (`HTIF5`) được bật (đã ghi ít nhất $16.384\text{ mẫu} \ge 20\%$).
   * **Chế độ Free-Run:** Bỏ qua ngắt EXTI; khi cờ `HTIF5` bật, kích hoạt ngay `TIM2` One-Pulse, không đếm timeout.
   * **Timeout Động:** $T_{\text{mcu-timeout}} = \frac{16384}{f_s} + 2.0\text{ s}$ đếm bằng `SysTick_Handler()`. Hết timeout mà chưa có trigger $\rightarrow$ MCU tự dừng và gửi Status `0x02`.
5. **Cơ chế Xoay vòng Bộ đệm (Buffer Unrolling):**
   * Do DMA chạy Circular, khi dừng lấy mẫu, con trỏ ghi `write_pos = 32768 - DMA2_Stream5->NDTR` là vị trí của mẫu cũ nhất ($t_0$).
   * Firmware có nhiệm vụ truyền xoay vòng từ `write_pos` đến cuối mảng rồi tiếp tục từ đầu mảng đến `write_pos - 1`, đảm bảo mốc trigger luôn cố định tại mẫu $t_{6554}$ (`trig_offset = 6554`) và dữ liệu liền mạch cả khi Timeout.
6. **Khóa Lệnh khi Truyền (`TRANSFERRING`):**
   * MCU bỏ qua hoàn toàn (drop) mọi byte nhận được từ USB, không phát sinh NAK/PONG chen ngang vào luồng truyền 32KB.
   * Khi ở các trạng thái bắt tín hiệu (`ARMED`, `PRE_SAMPLING`, `WAIT_TRIGGER`, `POST_SAMPLING`): nhận `CMD_START` mới $\rightarrow$ trả NAK `ERR_BUSY` (`0xE3`); nhận `CMD_PING` $\rightarrow$ trả `RSP_PONG` (`0x04`); nhận `CMD_ABORT` $\rightarrow$ dừng khẩn cấp và trả `RSP_ABORTED` (`0x05`).

---

## 5. Quy Tắc Thời Gian Thực Cho ISR, DMA & Concurrency

1. **Trình phục vụ ngắt siêu gọn (ISR < 30 dòng):**
   * Trong ISR chỉ thực hiện: xóa cờ ngắt, ghi thanh ghi điều khiển thiết yếu, hoặc thay đổi cờ trạng thái FSM.
   * **TUYỆT ĐỐI CẤM TRONG ISR:** Không gọi `printf()`, không gọi `HAL_Delay()`, không thực hiện tính toán nặng (vòng lặp XOR 32KB), không chờ vòng lặp truyền USB (`TxState`).
2. **Biến dùng chung giữa ISR và Main:**
   * Mọi biến trạng thái chia sẻ giữa ISR và luồng chính (`main.c`) bắt buộc phải khai báo `volatile` và dùng kiểu số nguyên độ rộng cố định (`uint32_t`, `uint8_t`, `bool`).
3. **Quản trị Cờ ngắt & DMA sạch sẽ:**
   * Phải xóa cờ ngắt theo đúng trình tự hướng dẫn trong ST RM0368.
   * Trước khi kích hoạt một lượt Capture mới, bắt buộc phải xóa sạch cờ Half-Transfer (`HTIF5`), Transfer-Complete (`TCIF5`), và các cờ lỗi DMA Stream5 (`TEIF5`, `DMEIF5`, `FEIF5`).
4. **Bảo vệ truyền USB-CDC (`TxState` Watchdog):**
   * Truyền gói tin 32.776B theo từng khối block 512B bằng `CDC_Transmit_FS()`.
   * Luôn kiểm tra cờ `hcdc->TxState == 0` trước khi gửi khối tiếp theo.
   * Kèm timeout bảo vệ $100\text{ ms}$ cho mỗi block. Nếu quá hạn do đứt cáp hoặc phần mềm PC tắt đột ngột $\rightarrow$ giải phóng trạng thái và cưỡng bức đưa FSM về `IDLE`.
5. **Kiểm tra mã trả về của ST HAL:**
   * Không bao giờ bỏ qua giá trị trả về kiểu `HAL_StatusTypeDef` từ các hàm thư viện của ST.

---

## 6. Tiêu Chuẩn Phong Cách Mã Nguồn C (C11 Nhúng An Toàn)

1. **Chuẩn ngôn ngữ:** C11 (GCC ARM Embedded). Không viết mã C++.
2. **Kiểu dữ liệu:** Bắt buộc include `<stdint.h>` và `<stdbool.h>`. Tuyệt đối không dùng kiểu `int`, `short`, `long` trần cho dữ liệu phần cứng hoặc giao thức.
3. **Quản lý bộ nhớ:**
   * **CẤM DÙNG CẤP PHÁT ĐỘNG (`malloc`, `free`)**.
   * CẤM đệ quy (recursion).
   * CẤM mảng kích thước biến động trên stack (VLA - Variable Length Arrays).
   * Bộ đệm mẫu 32 KB phải khai báo tĩnh: `static uint8_t la_capture_buffer[32768];`.
4. **Quy ước đặt tên (Naming Conventions):**
   * Hàm nghiệp vụ: `la_<module>_<action>` (ví dụ: `la_core_start_capture`, `la_protocol_send_control_frame`).
   * Macro và Hằng số: `LA_<NAME>` (ví dụ: `LA_BUFFER_SIZE`, `LA_TRIG_OFFSET_DEFAULT`).
   * Trạng thái FSM: `enum` có tiền tố `LA_STATE_*`.
5. **Cấu trúc điều khiển:** Mọi lệnh `switch` bắt buộc phải có nhánh `default`.
6. **Hằng số phần cứng:** Các giá trị như `ARR = 13`, `26213`, `6554` phải được định nghĩa bằng `#define` hoặc mảng `const` kèm comment giải thích công thức tính.

---

## 7. Lộ Trình Triển Khai Firmware Theo Từng Bước (Phased Roadmap)

Khi xây dựng hoặc nâng cấp firmware, Agent phải tuân thủ thứ tự 4 bước sau, không nhảy cóc:

```text
[Bước 1: Free-Run Base]       -> Chạy thông luồng TIM1 -> DMA2 -> Buffer 32KB -> USB-CDC gửi dữ liệu lên PC.
             │
[Bước 2: Loopback Self-Test]  -> Cấu hình USART1 TX trên PA9 phát mẫu test 115200 bps nối sang PA0.
             │
[Bước 3: Full FSM Trigger]    -> Ghép nối ngắt DMA Half-Transfer -> Unmask EXTI -> Kích TIM2 One-Pulse -> Unroll Buffer.
             │
[Bước 4: Edge Cases & Polish] -> Hoàn thiện Timeout động SysTick, Ping, Abort, NAK và Watchdog USB 100ms.
```

---

## 8. Tiêu Chí "Dừng Lại Và Hỏi" (Stop & Ask Criteria)

Agent phải dừng lại, nêu rõ vấn đề và hỏi ý kiến TV1 khi gặp các tình huống sau:
1. **Yêu cầu chạm vào file bị cấm:** Khi công việc đòi hỏi sửa các file ngoài danh mục mục 3.1.
2. **Mâu thuẫn đặc tả:** Khi phát hiện điểm xung đột giữa `spec/protocol.md` và `spec/logic_analyzer_specification.md`, hoặc khi yêu cầu người dùng vi phạm kiến trúc mục 4.
3. **Thay đổi cấu hình cốt lõi:** Khi cần can thiệp vào tần số SYSCLK 84 MHz, phân chia clock APB, kênh DMA request hoặc bảng ưu tiên NVIC.
4. **Mơ hồ về hành vi thanh ghi:** Khi RM0368 không ghi rõ hoặc có dấu hiệu errata của chip.
5. **Nguyên tắc trung thực kỹ thuật (Intellectual Honesty):**
   * Nếu tính năng chỉ mới kiểm tra trên mô phỏng hoặc phân tích mã nguồn mà chưa nạp kit thật, **Agent BẮT BUỘC PHẢI NÓI RÕ LÀ "chưa kiểm chứng trên phần cứng thật"**, tuyệt đối không tự nhận là "đã chạy chính xác 100%".

---

## 9. Định Dạng Báo Cáo Nghiệm Thu & Quy Trình Git

### 9.1. Định dạng Báo cáo Nghiệm thu (Bắt buộc cho mỗi lượt trả lời hoàn thành task):
Mỗi khi thông báo hoàn thành một tính năng firmware, Agent phải trình bày rõ 3 mục:
1. **Đã thay đổi những gì:** Danh sách file và tóm tắt ngắn gọn các hàm/dòng đã sửa.
2. **Đã kiểm chứng bằng cách nào:** Kết quả biên dịch (0 error, 0 warning), kiểm tra map file SRAM, hoặc chạy test vector parser.
3. **Điều gì CHƯA thể kiểm chứng:** Các phần cần kit STM32F401, USB analyzer hoặc máy hiện sóng đo thực tế.

### 9.2. Quy chuẩn Git:
* Nhánh làm việc có tiền tố `fw/` (ví dụ: `fw/tim1-dma-capture`, `fw/cdc-protocol`).
* Commit chuẩn Conventional Commits: `feat(firmware): ...`, `fix(firmware): ...`.
* Tuyệt đối không commit file build rác (`*.o`, `*.elf`, thư mục `Debug/`, `Release/`). Giữ nguyên cấu hình `firmware/STM32F401_STLink.launch`.

---

## 10. Bảng Kiểm Tra Bắt Buộc Trước Khi Báo Hoàn Thành (Checklist)

| Hạng mục kiểm tra | Cách thực hiện | Tiêu chuẩn Đạt |
| :--- | :--- | :--- |
| **Bảo vệ mã CubeMX** | Rà soát `main.c`, `stm32f4xx_it.c`, `usbd_cdc_if.c` | 100% code tự viết nằm gọn trong `/* USER CODE BEGIN ... */` và `/* USER CODE END ... */`. |
| **Biên dịch** | Build trong STM32CubeIDE (`Ctrl+B`) hoặc CLI Make/CMake | **0 errors, 0 warnings**. |
| **Định dạng số** | `grep -rn "0x9A" firmware/` | Khớp Little-Endian `0x9A, 0x19` và `0x00, 0x80`. |
| **Dung lượng SRAM** | Tra cứu file `.map` sau khi biên dịch | Tổng dung lượng RAM < 64 KB (buffer 32 KB chiếm đúng 50%). |
| **Trạng thái Git** | Chạy `git status` | Không có file nhị phân rác hoặc file cấu hình tạm của IDE bị đưa vào git. |

---

*Tài liệu này là quy chuẩn hoạt động tối cao cho mọi AI Agent khi đồng hành cùng TV1 phát triển Firmware Logic Analyzer.*
