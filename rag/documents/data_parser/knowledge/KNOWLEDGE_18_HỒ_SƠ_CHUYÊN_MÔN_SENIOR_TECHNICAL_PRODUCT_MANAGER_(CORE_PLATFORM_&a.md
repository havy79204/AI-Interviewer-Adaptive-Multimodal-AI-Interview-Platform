## [TÀI LIỆU 18] HỒ SƠ CHUYÊN MÔN: SENIOR TECHNICAL PRODUCT MANAGER (CORE PLATFORM &amp; MICROSERVICES STRATEGY)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Senior Technical Product Manager (TPM) / Platform Product Manager.
- Domain ứng dụng: Nền tảng Fintech đa dịch vụ, E-commerce đa quốc gia, Hệ thống hạ tầng API (API-as-a-Product), Nền tảng Siêu ứng dụng (Super-app).
- Mục tiêu then chốt của vị trí: Định hình chiến lược và lộ trình phát triển cho các thành phần nền tảng dùng chung (Shared Services: API Gateway, Auth/IAM, Notification, Payment Hub); biến hạ tầng kỹ thuật phức tạp thành các dịch vụ nội bộ có tính module hóa cao; bảo đảm tính mở rộng và cân bằng giữa tốc độ phát triển tính năng của các Feature Teams với độ bền vững của Core Platform.
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Khách hàng trực tiếp (Internal Customers): 10-20 Feature Teams (Checkout, Search, Promotion, Logistics...), các kỹ sư Backend/Frontend tiêu thụ API nền tảng.
- Thượng nguồn: Thảo luận cùng VP of Engineering, Enterprise Architect để đồng nhất định hướng kiến trúc dài hạn và ngân sách hạ tầng.
- Hạ nguồn: Làm việc hàng ngày cùng Core Engineering Team (Principal Engineers, SREs, Security) để bóc tách yêu cầu thành Tech Specs, API Contracts và quản trị backlog nền tảng.
- Giao tiếp ngang: Phối hợp cùng Developer Relations (DevRel) xây dựng tài liệu kỹ thuật, SDK và cổng Developer Portal nội bộ.
3. Ngăn xếp công nghệ xu hướng &amp; Tiêu chuẩn ngành
- Giao thức &amp; Chuẩn kết nối: gRPC / Protocol Buffers (nội bộ microservices), RESTful API chuẩn OpenAPI 3.1, GraphQL Federation, AsyncAPI cho kiến trúc hướng sự kiện.
- Bảo mật &amp; Định danh: OAuth 2.1, OpenID Connect (OIDC), JWT, Zero Trust API Security, Mutual TLS (mTLS).
- Cơ chế kiểm soát lưu lượng: Rate Limiting (Token Bucket / Leaky Bucket), Circuit Breaker, Idempotency Standard.
- Chỉ số quản trị nền tảng: SLA/SLO/SLI, Error Budget, MTTR, P99 Latency, API Adoption Rate.

## 4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành

- Hiện tượng Phá vỡ tương thích ngược (Breaking Changes Catastrophe):
- Vấn đề: Đội ngũ Core Platform cập nhật một trường dữ liệu trong API xác thực người dùng, khiến 4 ứng dụng vệ tinh của các nhóm tính năng khác bị crash đồng loạt trên môi trường Production.
- Bản chất: Thiếu chiến lược quản lý phiên bản (API Versioning) và không có cơ chế kiểm thử hợp đồng ràng buộc (Contract Testing).
- Giải pháp: Thiết lập quy chuẩn bắt buộc: Không bao giờ xóa hoặc đổi kiểu dữ liệu của một trường đang tồn tại trong response; áp dụng cơ chế đánh dấu lỗi thời (Deprecation Policy) tối thiểu 6 tháng kèm log theo dõi mức độ sử dụng; tích hợp Pact.io vào CI/CD để tự động chặn các bản build phá vỡ hợp đồng của người tiêu thụ API.
- Xung đột ưu tiên giữa "Nợ kỹ thuật" (Tech Debt) và "Tính năng mới" (Business Features):
- Vấn đề: Các Feature Teams liên tục đòi hỏi Core Platform phải hỗ trợ ngay các API đặc thù phục vụ chiến dịch kinh doanh trước mắt, trong khi hệ thống Core đang có nguy cơ sập vì cơ sở dữ liệu phân tán chưa được sharding.
- Giải pháp: Áp dụng công thức phân bổ nguồn lực cứng theo tỷ lệ 60/30/10: 60% cho tính năng nền tảng dùng chung; 30% cho Tech Debt, tối ưu hiệu năng và nâng cấp bảo mật; 10% cho các sáng kiến thử nghiệm (R&amp;D). Mọi yêu cầu mang tính cục bộ từ một team đơn lẻ sẽ được hướng dẫn tự mở rộng qua cơ chế plugin/webhook thay vì sửa thẳng vào Core.

## 5. Tương tác chuyên môn &amp; Phản biện kỹ thuật

- Xử lý tình huống tranh luận kiến trúc: REST vs. GraphQL cho Core Platform:
- Tình huống: Nhóm Frontend yêu cầu Core Platform phải chuyển toàn bộ sang GraphQL để họ chủ động lấy dữ liệu tùy biến mà không cần nhờ Backend viết thêm API.
- Luận điểm phản biện của TPM: Phân tích rõ sự đánh đổi (Trade-offs): GraphQL rất tốt cho tầng trải nghiệm người dùng (BFF - Backend for Frontend), nhưng nếu dùng làm Core Platform kết nối hàng chục microservices phía sau sẽ tạo ra rủi ro nghiêm trọng về tấn công vét cạn tài nguyên (N+1 query problem, Deeply nested queries), mất khả năng caching ở tầng CDN/HTTP Gateway, và khó kiểm soát bảo mật theo quyền hạn chi tiết. Đề xuất: Core Platform giữ nguyên gRPC/REST hiệu năng cao, các nhóm Frontend tự xây dựng tầng BFF bằng GraphQL nếu có nhu cầu.

## 6. Môi trường tác nghiệp &amp; Công cụ thực tế

- Hạ tầng làm việc: Postman Workspace tập trung cho toàn công ty, Confluence lưu trữ các bản Architecture Decision Records (ADRs), bảng Kanban quản trị phụ thuộc (Cross-team Dependency Board) trên Linear/Jira.
- Màn hình theo dõi: Datadog Service Catalog hiển thị bản đồ phụ thuộc mạng nhện giữa các dịch vụ, lưu lượng gọi API và lượng tiêu hao ngân sách lỗi (Error Budget Consumption).