## [TÀI LIỆU 16] HỒ SƠ CHUYÊN MÔN: DATABASE ADMINISTRATOR &amp; STORAGE SPECIALIST (QUERY TUNING &amp; HIGH AVAILABILITY)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Database Administrator (DBA) / Database Reliability Engineer (DBRE).
- Domain ứng dụng: Hệ thống lõi ngân hàng (Core Banking), Cổng thanh toán, Hệ thống viễn thông, Sàn giao dịch tài sản điện tử.
- Mục tiêu then chốt của vị trí: Đảm bảo tính toàn vẹn (ACID), tính khả dụng liên tục (High Availability 99.999%), bảo vệ dữ liệu chống mất mát (RPO = 0) và tối ưu hóa hiệu năng truy xuất cơ sở dữ liệu ở mức phần cứng và thuật toán lưu trữ.
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn: Tiếp nhận các bản thiết kế mô hình dữ liệu (ERD) và các bản cập nhật lược đồ (Schema Migrations) từ Backend Engineers.
- Hạ nguồn: Cung cấp hạ tầng cơ sở dữ liệu ổn định, các bản Read Replicas tối ưu cho BI/Data Engineering Team; hỗ trợ SRE cấu hình giám sát I/O đĩa và bộ nhớ đệm.
- Giao tiếp ngang: Phối hợp cùng Security Team để cấu hình mã hóa dữ liệu tại chỗ (Transparent Data Encryption - TDE), phân quyền truy cập tối thiểu (Least Privilege) và kiểm toán truy cập dữ liệu nhạy cảm.
3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc lõi
- Hệ quản trị CSDL Quan hệ &amp; Phân tán: PostgreSQL (công nghệ thống trị các hệ thống hiện đại), MySQL/Percona, Oracle Database, CockroachDB / TiDB (NewSQL phân tán).
- Công cụ Quản trị &amp; Đồng bộ: Patroni (HA template cho PostgreSQL dùng etcd), PgBouncer (Connection Pooling), Debezium, Liquibase / Flyway (Schema Versioning).
- Giám sát &amp; Chẩn đoán hiệu năng: pg\_stat\_statements, PMM (Percona Monitoring and Management), pgBadger, Prometheus Postgres Exporter.
- Lưu trữ &amp; Sao lưu: WAL-G, pgBackRest, NVMe SSD tuning, ZFS / XFS filesystem optimization.

## 4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành

- Hiện tượng Tê liệt do Bế tắc (Deadlock Crisis) &amp; Cháy kết nối (Connection Pool Exhaustion):
- Vấn đề: Vào khung giờ khuyến mãi, ứng dụng đột ngột sập, trả về lỗi FATAL: remaining connection slots are reserved for non-replication superuser connections. Các câu lệnh UPDATE bị treo vô thời hạn.
- Bản chất kỹ thuật: Hàng nghìn tiến trình ứng dụng mở kết nối trực tiếp vào DB thay vì dùng bể kết nối; các giao dịch cập nhật nhiều bảng theo thứ tự ngược nhau gây ra hiện tượng Deadlock vòng tròn.
- Giải pháp: Đặt PgBouncer ở chế độ Transaction Pooling phía trước PostgreSQL để gom hàng chục nghìn kết nối từ ứng dụng thành vài trăm kết nối thực tế xuống DB; thiết lập statement\_timeout và lock\_timeout để tự động hủy các giao dịch bị kẹt quá 5 giây; chuẩn hóa thứ tự khóa tài nguyên (Lock Ordering) trong mã nguồn ứng dụng.
- Hiện tượng Transaction ID Wraparound (Khủng hoảng đóng băng DB trong PostgreSQL):
- Vấn đề: Cơ sở dữ liệu PostgreSQL đột ngột dừng mọi thao tác ghi dữ liệu, chuyển sang chế độ Read-only để tránh mất mát dữ liệu do cạn kiệt số lượng Transaction ID (vượt ngưỡng 2 tỷ transactions).
- Giải pháp: Cấu hình thông số autovacuum linh hoạt: Tăng số lượng worker, nâng cao maintenance\_work\_mem, giảm autovacuum\_vacuum\_cost\_limit để tiến trình Vacuum diễn ra liên tục, dọn dẹp các bản ghi chết (Dead Tuples) và freeze Transaction IDs kịp thời trước khi chạm ngưỡng nguy hiểm.

## 5. Tương tác chuyên môn &amp; Phản biện kỹ thuật

- Phản biện việc đánh Index bừa bãi của Lập trình viên:
- Tình huống: Lập trình viên backend yêu cầu tạo thêm 15 index mới trên một bảng có 50 triệu dòng dữ liệu để phục vụ việc tìm kiếm các trường lọc khác nhau trên giao diện.
- Luận điểm phản biện: DBA chứng minh trên môi trường test: Việc thêm 15 index làm tăng gấp 3 lần thời gian thực thi của các lệnh INSERT/UPDATE (do DB phải cập nhật lại 15 cây B-Tree cho mỗi bản ghi mới) và phình to dung lượng RAM đệm (Buffer Pool). Hướng dẫn lập trình viên sử dụng Composite Index (Chỉ mục kết hợp) chuẩn thứ tự hoặc Partial Index (Chỉ mục một phần có điều kiện WHERE) chỉ bao phủ các trạng thái dữ liệu thường xuyên được tìm kiếm.

## 6. Môi trường tác nghiệp &amp; Công cụ thực tế

- Hạ tầng làm việc: Terminal SSH kết nối trực tiếp vào các máy chủ DB thông qua mạng nội bộ bảo mật (Bastion Host / VPN), màn hình hiển thị liên tục biểu đồ I/O Wait, IOPS đĩa cứng và dung lượng lưu trữ phân vùng WAL.
- Bộ cẩm nang ứng cứu: Tài liệu quy trình khôi phục sau thảm họa (Disaster Recovery Runbook) được in ra giấy vật lý lưu trong tủ hồ sơ để sử dụng khi hệ thống mạng nội bộ bị ngắt kết nối hoàn toàn.