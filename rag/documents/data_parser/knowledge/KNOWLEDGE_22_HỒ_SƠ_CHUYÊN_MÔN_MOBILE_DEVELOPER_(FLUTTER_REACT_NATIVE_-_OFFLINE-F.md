## [TÀI LIỆU 22] HỒ SƠ CHUYÊN MÔN: MOBILE DEVELOPER (FLUTTER / REACT NATIVE - OFFLINE-FIRST &amp; APP VITALS)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Mobile Application Engineer (Cross-Platform: Flutter / React Native).
- Domain ứng dụng: Ứng dụng Tài chính / Ví điện tử, Ứng dụng Dành cho Tài xế / Giao vận ngoài thực địa, Ứng dụng Bán hàng tại điểm (mPOS), Mạng xã hội nội dung ngắn.
- Mục tiêu then chốt của vị trí: Xây dựng ứng dụng di động đa nền tảng (iOS &amp; Android) từ một mã nguồn duy nhất với hiệu năng tiệm cận ứng dụng gốc (Native Performance); làm chủ kiến trúc hoạt động khi mất mạng (Offline-First); đảm bảo các chỉ số ổn định sống còn của ứng dụng di động (Crash-free users rate &gt; 99.8%, thời gian khởi động app &lt; 2 giây).
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn: Nhận bản thiết kế giao diện chi tiết, animation transitions từ UI/UX Designer; nhận tài liệu API contracts từ Backend Team.
- Hạ nguồn: Phối hợp cùng Release Manager và Security Team để ký chứng thực ứng dụng (Code Signing), vượt qua các vòng kiểm duyệt khắt khe của Apple App Store và Google Play Store.
- Giao tiếp ngang: Làm việc cùng Mobile QA để phân tích các báo cáo lỗi xảy ra trên các dòng máy chuyên biệt (Vendor-specific bugs như Xiaomi MIUI, Samsung OneUI).
3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc di động
- Cross-Platform Frameworks: Flutter (Dart, Skia / Impeller Rendering Engine), React Native (TypeScript, New Architecture: JSI, Fabric Renderer, TurboModules).
- Kiến trúc Mã nguồn &amp; State Management: Clean Architecture, BLoC / Riverpod (Flutter), Zustand / Redux Toolkit (React Native).
- Lưu trữ Cục bộ &amp; Cơ sở dữ liệu Nhúng: SQLite, WatermelonDB, Isar, Realm, MMKV (Key-Value storage siêu tốc thay thế SharedPreferences/AsyncStorage).
- Đồng bộ Dữ liệu Ngoại tuyến: PowerSync, Couchbase Lite, CRDTs (Conflict-free Replicated Data Types).
- Giám sát Sức khỏe Ứng dụng (Mobile Vitals): Firebase Crashlytics, Sentry Mobile, Datadog RUM, New Relic Mobile.
4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành
- Kiến trúc Đồng bộ Dữ liệu Ngoại tuyến (Offline-First Sync Engine):
- Vấn đề: Tài xế giao hàng phải thao tác quét mã đơn hàng trong tầng hầm chung cư hoàn toàn không có sóng 3G/4G. Ứng dụng không được phép báo lỗi quay vòng, mà phải ghi nhận tức thì và tự động gửi dữ liệu về máy chủ ngay khi có mạng trở lại mà không làm mất mát hoặc ghi đè sai lệch dữ liệu.
- Bản chất: Xung đột dữ liệu hai chiều giữa trạng thái cục bộ trên thiết bị và cơ sở dữ liệu trung tâm khi kết nối mạng chập chờn.
- Giải pháp: Lưu trữ toàn bộ thao tác vào hàng đợi cục bộ (Local Outbox Queue) bằng cơ sở dữ liệu nhúng có hỗ trợ Transaction (SQLite/Isar); thiết lập cơ chế Optimistic UI (cập nhật giao diện thành công ngay lập tức để người dùng tiếp tục thao tác); khi có mạng, một tiến trình chạy ngầm (Background Worker) sẽ đẩy các bản ghi trong Outbox lên theo thứ tự kèm dấu thời gian logic (Logical Timestamp); áp dụng chiến lược giải quyết xung đột (Conflict Resolution: Last-Write-Wins hoặc phân xử dựa trên nghiệp vụ cụ thể).
- Hiện tượng Tràn bộ nhớ &amp; Rò rỉ tài nguyên trên thiết bị cấu hình thấp:
- Vấn đề: Người dùng lướt danh sách tin tức chứa nhiều hình ảnh và video một lúc thì ứng dụng bị hệ điều hành tự động đóng cưỡng bức (Out-of-Memory Crash).
- Giải pháp: Tái sử dụng vùng nhớ hiển thị: Triển khai danh sách ảo hóa (ListView.builder trong Flutter hoặc FlashList trong React Native); sử dụng thư viện tải ảnh thông minh có cơ chế tự động giải mã ảnh theo đúng kích thước hiển thị trên màn hình thay vì tải ảnh gốc dung lượng lớn vào RAM; hủy đăng ký (Dispose/Unsubscribe) toàn bộ các luồng lắng nghe sự kiện (Streams, Listeners, Timers) trong vòng đời đóng màn hình.
5. Tương tác chuyên môn &amp; Phản biện kỹ thuật
- Phản biện việc lạm dụng thư viện bên thứ ba (Third-party Dependency Hell):
- Tình huống: Lập trình viên muốn cài đặt thêm 15 thư viện plugin khác nhau từ cộng đồng npm/pub.dev chỉ để làm vài hiệu ứng chuyển động nhỏ và một nút bấm đơn giản.
- Luận điểm phản biện của Mobile Lead: Phân tích các rủi ro hệ trọng đối với ứng dụng di động: Cài nhiều thư viện không rõ nguồn gốc sẽ làm phình to dung lượng tải về của tệp .ipa/.apk (mỗi 6MB tăng thêm làm giảm 1% tỷ lệ cài đặt thành công); tăng nguy cơ ứng dụng bị Apple từ chối duyệt do vi phạm các chính
27. sách quyền riêng tư (Privacy Manifests); và tiềm ẩn nguy cơ xung đột mã nguồn gốc khi nâng cấp phiên bản hệ điều hành Android/iOS mới. Yêu cầu: Đội ngũ tự tay viết các đoạn mã ngắn cho các tính năng cơ bản, chỉ sử dụng thư viện lớn của những tổ chức phát triển uy tín có cam kết duy trì lâu dài.
6. Môi trường tác nghiệp &amp; Công cụ thực tế
- Hạ tầng làm việc: Máy tính Mac chuyên dụng chạy hệ điều hành macOS (bắt buộc để biên dịch ứng dụng iOS), dàn máy điện thoại thử nghiệm thực tế thuộc nhiều phân khúc giá khác nhau được gắn cố định trên bàn làm việc.
- Bộ công cụ chẩn đoán: Android Studio Profiler, Xcode Instruments (Time Profiler, Leaks), công cụ kiểm tra độ sâu cây giao diện (Flutter DevTools Widget Inspector / React DevTools).