## [TÀI LIỆU 06] PHỎNG VẤN EMBEDDED &amp; IOT FIRMWARE ENGINEER (SMART HARDWARE &amp; RTOS)

1. Định vị chức danh &amp; Ngành nghề cốt lõi
- Vị trí: Embedded Software Engineer / IoT Firmware Specialist.
- Cấp bậc: Junior - Middle (1.5 - 3.5 năm kinh nghiệm).
- Domain tiêu biểu: Thiết bị thông minh gia đình (Smart Home), Thiết bị y tế cá nhân, Tự động hóa công nghiệp (IIoT), Thiết bị theo dõi vận tải (Fleet Tracking).
- Mục tiêu then chốt trong buổi phỏng vấn: Đánh giá sự hiểu biết thấu đáo về phần cứng và vi điều khiển (ARM Cortex-M, ESP32), kỹ năng lập trình C/C++ chuẩn an toàn (quản lý bộ nhớ, con trỏ), tư duy lập trình thời gian thực (RTOS) và kỹ năng chẩn đoán lỗi tín hiệu vật lý.
2. Hệ sinh thái vai trò &amp; Hội đồng phỏng vấn
- Người phỏng vấn chính: Hardware Engineering Lead, Senior Firmware Architect.
- Giao diện làm việc thực tế: Làm việc sát sườn với Hardware/PCB Designer (kiểm tra schematic, chân GPIO), Cloud Backend Dev (thống nhất định dạng gói tin MQTT/JSON/Protobuf) và Kỹ sư thử nghiệm cơ khí/vỏ hộp.
3. Công nghệ xu hướng &amp; Khái niệm bắt buộc
- Vi điều khiển &amp; Nền tảng: STM32 family, ESP-IDF, Nordic nRF (Bluetooth Low Energy), Raspberry Pi Pico.
- RTOS &amp; Đa nhiệm: FreeRTOS / Zephyr RTOS (Task scheduling, Mutex, Priority Inversion, Semaphore).
- Giao thức kết nối: UART, SPI, I2C, CAN Bus, BLE 5.x, Zigbee, Matter standard, Cellular IoT (LTE-M/NB-IoT).
- Kỹ năng gỡ lỗi phần cứng: Sử dụng Digital Storage Oscilloscope, Logic Analyzer, GDB với J-Link/ST-Link, đọc datasheet linh kiện.
4. Kịch bản phỏng vấn kỹ thuật &amp; Tình huống "bắt bài"
- Câu hỏi bản chất bộ nhớ &amp; Con trỏ C (C Pointer Gotchas): "Hàm C sau đây có điểm gì cực kỳ nguy hiểm có thể làm sập (Crash) toàn bộ hệ thống nhúng?"
- C

```
char* get_sensor_status() { char buffer[32]; snprintf(buffer, sizeof(buffer), "STATUS_OK"); return buffer; }
```

●

- Kỳ vọng: Chỉ ra ngay lỗi trả về con trỏ trỏ tới vùng nhớ cục bộ trên Stack (buffer). Khi hàm kết thúc, stack frame bị thu hồi, con trỏ trở thành con trỏ hoang (Dangling Pointer), truy cập vào sẽ gây lỗi Undefined Behavior hoặc HardFault trên vi điều khiển. Giải pháp: Truyền con trỏ buffer từ bên ngoài vào hàm hoặc dùng biến static (nếu không cần re-entrant).
- Tình huống lập trình thời gian thực (Priority Inversion): "Hiện tượng Đảo ngược mức ưu tiên (Priority Inversion) trong FreeRTOS là gì và hệ quả của nó nguy hiểm thế nào đối với các thiết bị thời gian thực? Làm thế nào để giải quyết?"
- Kỳ vọng: Mô tả được kịch bản: Task ưu tiên thấp giữ Mutex tài nguyên ➔ Task ưu tiên trung bình chiếm quyền CPU của Task thấp ➔ Task ưu tiên cao cần tài nguyên bị chặn vô thời hạn. Giải pháp: Kỹ thuật Priority Inheritance (Kế thừa quyền ưu tiên) - tạm thời nâng mức ưu tiên của Task thấp lên bằng Task cao cho đến khi nó giải phóng Mutex.
- Bài toán tiết kiệm năng lượng (Low-power Optimization): "Thiết bị cảm biến nhiệt độ chạy bằng pin đồng xu CR2032 (dung lượng 220mAh) của công ty yêu cầu phải hoạt động liên tục tối thiểu 2 năm ngoài thực địa. Bạn sẽ thiết kế luồng xử lý phần mềm như thế nào?"
- Kỳ vọng: Vi điều khiển 99% thời gian phải ở chế độ Deep Sleep (tiêu thụ dòng cỡ micro-ampe); chỉ thức dậy bằng Timer ngắt định kỳ hoặc ngắt ngoài của cảm biến; sau khi thức dậy dùng DMA đọc nhanh dữ liệu qua I2C, gửi bản tin nén ngắn qua BLE/Zigbee trong vài chục mili-giây rồi lập tức chuyển về trạng thái Deep Sleep; tắt toàn bộ các bộ dao động (Clocks) và chân GPIO không dùng đến.
5. Sự cố phòng phỏng vấn &amp; Cách làm chủ không gian
- Môi trường Online:
- Sự cố: Được yêu cầu giải thích một sơ đồ mạch điện tử (Schematic) trên file PDF nhưng màn hình chia sẻ quá mờ hoặc người phỏng vấn chỉ vào linh kiện không rõ ràng.
- Xử lý: Chủ động hỏi số hiệu linh kiện (RefDes, ví dụ: R12, C5, U2) để định vị chính xác; phóng to màn hình vào đúng khu vực mạch đang bàn luận và xác nhận lại với người phỏng vấn trước khi bắt đầu phân tích tín hiệu.
- Môi trường Onsite (Vật dụng &amp; Phần cứng thực tế):
- Khi người phỏng vấn đưa cho bạn một bo mạch thực tế (PCB): Đừng vội vàng cầm tay trần bóp chặt vào các chân chip linh kiện (thể hiện sự thiếu chuyên nghiệp về tĩnh điện - ESD). Hãy cầm vào cạnh bảng mạch (PCB edges), quan sát kỹ các khối nguồn, khối vi điều khiển, thạch anh, ăng-ten trước khi bắt đầu trả lời.