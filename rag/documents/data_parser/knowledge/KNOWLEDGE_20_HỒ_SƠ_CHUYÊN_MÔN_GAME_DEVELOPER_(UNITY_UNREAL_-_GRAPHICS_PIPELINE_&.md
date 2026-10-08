## [TÀI LIỆU 20] HỒ SƠ CHUYÊN MÔN: GAME DEVELOPER (UNITY / UNREAL - GRAPHICS PIPELINE &amp; PHYSICS)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Game Developer / Graphics &amp; Gameplay Programmer.
- Domain ứng dụng: Game 3D Mobile/PC, Trò chơi đa người chơi thời gian thực (Real-time Multiplayer), Trải nghiệm thực tế ảo/tăng cường (VR/AR), Mô phỏng tương tác 3D.
- Mục tiêu then chốt của vị trí: Hiện thực hóa các ý tưởng của Game Designer thành cơ chế tương tác mượt mà, chân thực; làm chủ việc cân bằng tài nguyên phần cứng để duy trì tốc độ khung hình ổn định (Khóa 60 FPS / 120 FPS); triệt tiêu độ giật lag đồ họa và tối ưu hóa bộ nhớ trên đa dạng thiết bị.
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn: Nhận tài liệu Game Design Document (GDD) từ Game Designer; tiếp nhận mô hình 3D, rigging, animations và hiệu ứng từ 3D Artists và Technical Artists.
- Hạ nguồn: Làm việc cùng Game Server / Backend Engineer để đồng bộ trạng thái nhân vật trong các trận đấu mạng và bảo mật logic giao dịch vật phẩm.
- Giao tiếp ngang: Phối hợp cùng Game QA / Testers để phân tích các lỗi va chạm (Clipping/Collision glitches) và tình trạng sụt giảm khung hình đột ngột (Frame Drops).
3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc game
- Game Engines &amp; Ngôn ngữ: Unity (C#, Universal Render Pipeline - URP), Unreal Engine 5 (C++, Nanite, Lumen, Chaos Physics).
- Lập trình Đồ họa &amp; Hiệu ứng: HLSL / GLSL Shaders, Shader Graph, GPU Instancing, Compute Shaders.
- Kiến trúc phần mềm: Entity Component System (ECS) / Data-Oriented Technology Stack (DOTS), State Machine, Object Pooling Pattern.
- Mạng đa người chơi &amp; Đồng bộ: Client-Side Prediction, Server Reconciliation, Snapshot Interpolation, Photon Fusion / Mirror.

## 4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành

- Hiện tượng Giật khung hình do Bộ thu gom rác (Garbage Collection Spikes):
- Vấn đề: Cứ sau mỗi 15-20 giây chiến đấu mượt mà, trò chơi trên điện thoại lại bị giật khựng lại khoảng 100ms, làm hỏng trải nghiệm combo của người chơi.
- Bản chất: Mã nguồn C# liên tục cấp phát bộ nhớ động trên Heap (sử dụng toán tử new trong vòng lặp Update(), nối chuỗi String liên tục, hoặc ép kiểu Boxing/Unboxing). Khi bộ nhớ đầy, trình Garbage Collector của Unity buộc phải dừng toàn bộ luồng xử lý game để dọn dẹp.
- Giải pháp: Áp dụng triệt để mô hình Object Pooling cho tất cả các đối tượng sinh ra nhiều lần (đạn, hiệu ứng nổ, quái vật, số hiển thị sát thương); thay thế chuỗi bằng mảng ký tự hoặc dùng StringBuilder dùng lại; sử dụng struct thay cho class cho các cấu trúc dữ liệu nhỏ, tạm thời để phân bổ trên Stack.
- Hiện tượng Quá tải Draw Calls &amp; Tắc nghẽn CPU/GPU:
- Vấn đề: Màn chơi có nhiều cây cối, nhà cửa và nhân vật khiến tổng số Draw Calls vọt lên hơn 1,000, khiến thiết bị di động bị nóng ran và pin sụt nhanh chóng.
- Giải pháp: Chuẩn hóa quy trình cùng 3D Artist: Gộp các tấm vân bề mặt nhỏ vào chung một tấm lớn (Texture Atlasing); kích hoạt cơ chế Occlusion Culling (không render những vật thể bị che khuất sau tường); sử dụng GPU Instancing cho các vật thể giống nhau (cỏ, cây, đá); thiết lập hệ thống Level of Detail (LOD) để giảm số lượng đa giác (Polygon count) khi vật thể ở xa camera.

## 5. Tương tác chuyên môn &amp; Phản biện kỹ thuật

- Phản biện bài toán "Xử lý va chạm trên Client hay Server" trong Game Multiplayer:
- Tình huống: Game Designer muốn tính toán toàn bộ việc bắn trúng đích (Hit Registration) trực tiếp trên điện thoại của người chơi để người chơi không bao giờ cảm thấy bị trễ (Zero-latency feeling).
- Luận điểm phản biện của Kỹ sư Game: Chỉ ra rủi ro nghiêm trọng về gian lận (Game Hacking): Nếu để Client toàn quyền quyết định việc bắn trúng, các phần mềm hack sẽ dễ dàng chỉnh sửa bộ nhớ gửi gói tin "đã bắn trúng đầu" về máy chủ mà không cần bắn thực tế. Đề xuất giải pháp chuẩn công nghiệp: Client áp dụng Client-Side Prediction để hiển thị hiệu ứng trúng đạn trước mắt người chơi, nhưng Server là cơ quan quyền lực tối cao (Authoritative Server) thực hiện kỹ thuật Lag Compensation (tua lại thời gian thế giới game về đúng thời điểm người chơi bóp cò) để xác nhận phát bắn có hợp lệ hay không.

## 6. Môi trường tác nghiệp &amp; Công cụ thực tế

- Hạ tầng làm việc: Máy trạm cấu hình cực cao (GPU RTX dòng cao cấp, RAM tối thiểu 64GB phục vụ việc build mã nguồn C++ Unreal Engine), nhiều thiết bị di động test cắm dây cáp debug trực tiếp.
- Bộ công cụ chẩn đoán chuyên dụng: Unity Profiler, Frame Debugger (soi từng bước vẽ của GPU), RenderDoc, Xcode Instruments (theo dõi rò rỉ bộ nhớ trên iOS).