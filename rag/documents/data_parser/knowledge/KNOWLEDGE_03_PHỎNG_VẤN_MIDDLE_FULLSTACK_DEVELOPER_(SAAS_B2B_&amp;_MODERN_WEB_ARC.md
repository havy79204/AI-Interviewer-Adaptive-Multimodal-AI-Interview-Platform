## [TÀI LIỆU 03] PHỎNG VẤN MIDDLE FULLSTACK DEVELOPER (SAAS B2B &amp; MODERN WEB ARCHITECTURE)

1. Định vị chức danh &amp; Ngành nghề cốt lõi
- Vị trí: Middle Fullstack Developer (React/Next.js + Node.js/NestJS hoặc Python/Go).
- Cấp bậc: Middle (2.5 - 4 năm kinh nghiệm).
- Domain tiêu biểu: B2B SaaS, Nền tảng quản trị nhân sự/kế toán (ERP/CRM), Marketing Automation, Edtech.
- Mục tiêu then chốt trong buổi phỏng vấn: Kiểm chứng khả năng "bao sân" (End-to-End Ownership), tư duy thiết kế kiến trúc phân tầng (Clean Architecture), khả năng cân bằng giữa trải nghiệm giao diện mượt mà và tính bền vững của logic máy chủ.
2. Hệ sinh thái vai trò &amp; Hội đồng phỏng vấn
- Người phỏng vấn chính: Technical Lead, Engineering Manager.
- Giao diện làm việc thực tế: Làm việc độc lập với Product Manager (nhận User Story, làm rõ AC), UI/UX Designer (đánh giá tính khả thi kỹ thuật), trao đổi với DevOps về cấu hình môi trường triển khai.
3. Công nghệ xu hướng &amp; Khái niệm bắt buộc
- Modern Frontend: Next.js (App Router, Server Actions, RSC - React Server Components), TanStack Query, Zustand, Web Vitals optimization.
- Modern Backend: NestJS, TypeScript nâng cao (Generics, Decorators), ORM (Prisma / TypeORM), Event-driven patterns.
- Kiến trúc dữ liệu: Data Modeling cho Multi-tenant SaaS (Database-per-tenant vs Schema-per-tenant vs Shared Database), Redis caching patterns.
- Bảo mật Web: CORS, CSRF, XSS prevention, Content Security Policy (CSP), JWT lifecycle (Refresh Token Rotation).
4. Kịch bản phỏng vấn kỹ thuật &amp; Tình huống "bắt bài"
- Câu hỏi kiến trúc Fullstack: "Khi một người dùng tải một trang Dashboard B2B chứa 5 biểu đồ dữ liệu lớn, trang web bị trắng màn hình mất 4 giây rồi mới hiện ra. Bạn sẽ chia nhỏ việc phân tích và tối ưu hóa ở cả tầng Client lẫn Server như thế nào?"
- Kỳ vọng:
17. ■ Frontend: Dùng Streaming SSR với React Suspense để nạp khung xương (Skeleton) trước, chia nhỏ component tải bất đồng bộ; áp dụng memoization tránh re-render thừa.
18. ■ Backend/DB: Thay vì gọi 5 query nặng tuần tự, dùng Promise.all xử lý song song; phân tích Execution Plan của SQL, đánh composite index; lưu kết quả aggregated data vào Redis Cache với TTL hợp lý hoặc dùng materialized view.
- Câu hỏi bẫy (State &amp; Concurrency): "Bạn quản lý việc người dùng bấm nút Submit một form thanh toán 2 lần liên tiếp (Double-click) như thế nào để tài khoản của họ không bị trừ tiền 2 lần?"
- Kỳ vọng: Không được chỉ dựa vào việc disable nút bấm ở Frontend (vì người dùng có thể bypass qua Postman hoặc mạng lag). Bắt buộc phải có giải pháp ở Backend: Áp dụng Idempotency Key sinh từ Client gửi kèm trong Header, Backend lưu key này vào Redis với trạng thái PENDING và từ chối xử lý các request trùng lặp cho đến khi giao dịch đầu tiên hoàn tất.
- Tình huống xử lý xung đột kỹ thuật: "Product Manager yêu cầu tuần tới phải release gấp một tính năng nhưng nếu làm nhanh thì bạn buộc phải bỏ qua việc viết Unit Test và cấu trúc database sẽ bị 'hardcode' (Tech Debt). Bạn xử lý mâu thuẫn này thế nào?"
- Kỳ vọng: Thể hiện sự trưởng thành: Đồng ý với mục tiêu kinh doanh nhưng phải minh bạch rủi ro. Đề xuất phương án MVP tối giản tính năng thay vì viết ẩu; tạo ngay ticket Tech Debt trên Jira và cam kết lộ trình refactor ngay trong Sprint kế tiếp.
5. Sự cố phòng phỏng vấn &amp; Cách làm chủ không gian
- Môi trường Online:
- Sự cố: Máy tính cá nhân bị đơ, quạt tản nhiệt rú to khi mở IDE nặng hoặc Docker trong lúc đang phỏng vấn trực tuyến.
- Xử lý: Tắt bớt các ứng dụng chạy ngầm trước buổi phỏng vấn; chuẩn bị sẵn môi trường code online nhẹ nhàng (CodeSandbox, StackBlitz, Replit) để có thể demo ngay mà không phụ thuộc vào local environment.
- Môi trường Onsite:
- Tương tác cơ thể &amp; Ánh mắt: Khi vẽ sơ đồ trên bảng hoặc giải thích code trên máy tính, tuyệt đối tránh việc quay lưng hoàn toàn về phía người phỏng vấn quá lâu. Hãy đứng theo góc 45 độ, vừa vẽ vừa giao tiếp bằng ánh mắt để kiểm tra xem hội đồng có đang theo kịp luồng tư duy của mình hay không.