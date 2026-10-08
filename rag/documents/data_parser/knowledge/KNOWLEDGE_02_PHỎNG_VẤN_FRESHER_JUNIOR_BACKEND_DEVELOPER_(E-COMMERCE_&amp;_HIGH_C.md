## [TÀI LIỆU 02] PHỎNG VẤN FRESHER / JUNIOR BACKEND DEVELOPER (E-COMMERCE &amp; HIGH CONCURRENCY)

1. Định vị chức danh &amp; Ngành nghề cốt lõi
- Vị trí: Fresher / Junior Backend Developer (Node.js, Golang, Java hoặc Python).
- Cấp bậc: Entry-level / Junior (0 - 1.5 năm kinh nghiệm).
- Domain tiêu biểu: Sàn thương mại điện tử, Hệ thống Đặt chỗ trực tuyến (Ticketing/Booking), Logistics, Fintech.
- Mục tiêu then chốt trong buổi phỏng vấn: Đánh giá độ vững chắc của kiến thức nền tảng (OOP, Cấu trúc dữ liệu &amp; Giải thuật), bản chất cơ sở dữ liệu quan hệ (Index, Transaction, Lock) và thái độ tiếp thu khi được gợi ý.
2. Hệ sinh thái vai trò &amp; Hội đồng phỏng vấn
- Người phỏng vấn chính: Senior Backend Engineer, Technical Lead.
- Giao diện làm việc thực tế: Nhận task từ Tech Lead, làm việc với QA (fix bug, tái hiện lỗi), Frontend Dev (thống nhất hợp đồng API Swagger/REST) và DevOps (theo dõi build fail CI/CD).
3. Công nghệ xu hướng &amp; Khái niệm bắt buộc
- Kiến trúc &amp; Chuẩn API: RESTful API chuẩn RFC, gRPC cơ bản, Microservices fundamentals, Dependency Injection.
- Cơ sở dữ liệu &amp; Caching: PostgreSQL / MySQL, hiểu sâu B-Tree Index, N+1 query problem, Redis (Cache-aside, Key expiration).
- Message Broker cơ bản: Khái niệm Queue, Pub/Sub (RabbitMQ, Kafka cơ bản).
- Môi trường: Docker containerization, Git flow (Rebase vs Merge, Cherry-pick).
4. Kịch bản phỏng vấn kỹ thuật &amp; Tình huống "bắt bài"
- Câu hỏi nền tảng (Bản chất): "Chuyện gì thực sự xảy ra từ lúc bạn gõ một câu lệnh SELECT * FROM users WHERE email = 'abc@gmail.com' vào cơ sở dữ liệu cho đến khi nhận được kết quả?"
- Kỳ vọng: Phân tích được các bước: Parser kiểm tra cú pháp ➔ Query Optimizer lên kế hoạch thực thi ➔ Kiểm tra Index trên cột email (B-Tree traversal) ➔ Đọc dữ liệu từ Buffer Pool (RAM) hoặc Disk I/O ➔ Trả về tập kết quả.
- Tình huống bài toán thực tế (Concurrency): "Trong một chương trình Flash Sale, kho chỉ còn đúng 1 chiếc iPhone cuối cùng. Hai khách hàng nhấn nút 'Mua ngay' hoàn toàn cùng một mili-giây. Bạn thiết kế mã nguồn và database thế nào để không bao giờ xảy ra lỗi bán âm kho (Over-selling)?"
- Kỳ vọng: Ứng viên Fresher/Junior thường nói "dùng if(quantity &gt; 0)". Cần bẻ gãy câu trả lời này bằng bài toán Race Condition. Hướng đi đúng: Sử dụng Database Pessimistic Locking (SELECT ... FOR UPDATE), hoặc Optimistic Locking (kiểm tra version/quantity trong lệnh UPDATE items SET stock = stock - 1 WHERE id = 1 AND stock &gt; 0), hoặc sử dụng lệnh nguyên tử (Atomic decrement DECR) trên Redis.
- Live Coding &amp; Refactoring: Cho một đoạn code dài 30 dòng có lồng vòng lặp, query database bên trong vòng lặp (vấn nạn N+1), và không xử lý lỗi (Missing try-catch). Yêu cầu ứng viên tìm ra 3 điểm tệ nhất và viết lại.
5. Sự cố phòng phỏng vấn &amp; Cách làm chủ không gian
- Môi trường Online:
- Sự cố: Ứng viên run rẩy, gõ phím liên tục phát ra tiếng động to lấn át giọng nói hoặc quên không run code khi viết live coding.
- Xử lý: Bật tính năng chống ồn mic (Noise Cancellation); trước khi viết code, hãy luôn luôn tóm tắt lại đề bài và nêu ý tưởng giải pháp bằng lời trước để nhận được sự đồng thuận của người phỏng vấn: "Ý tưởng của em là dùng HashMap để giảm độ phức tạp từ xuống , anh/chị có thấy hợp lý không ạ?". 𝑂(𝑁2) 𝑂(𝑁)
- Môi trường Onsite:
- Sổ tay &amp; Bút viết: Ứng viên mang theo một cuốn sổ tay nhỏ và bút. Khi người phỏng vấn giải thích đề bài hoặc đưa ra gợi ý, hãy ghi nhanh các từ khóa xuống sổ. Điều này thể hiện sự tôn trọng, tác phong cẩn thận và giúp não bộ không bị quá tải thông tin.