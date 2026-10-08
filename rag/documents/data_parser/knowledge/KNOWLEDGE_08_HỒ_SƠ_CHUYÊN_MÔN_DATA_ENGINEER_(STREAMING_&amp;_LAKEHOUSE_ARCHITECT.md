## [TÀI LIỆU 08] HỒ SƠ CHUYÊN MÔN: DATA ENGINEER (STREAMING &amp; LAKEHOUSE ARCHITECTURE)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Data Engineer / Big Data Platform Engineer.
- Domain ứng dụng: Ngân hàng số, Sàn giao dịch tài chính, E-commerce Logistics, Hệ thống phân tích sự kiện IoT thời gian thực.
- Mục tiêu then chốt của vị trí: Xây dựng, bảo trì hạ tầng truyền tải và lưu trữ dữ liệu quy mô lớn (Batch &amp; Real-time); đảm bảo tính toàn vẹn (Data Integrity), độ trễ thấp (Low-latency) và quản trị dữ liệu tập trung (Data Governance).
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn: Tiếp nhận kết nối từ hàng trăm cơ sở dữ liệu giao dịch nghiệp vụ (PostgreSQL, MongoDB, MySQL) của Backend Team và hệ thống log sự kiện từ Mobile/Web apps.
- Hạ nguồn: Cung cấp các bảng dữ liệu tầng Gold chuẩn hóa cho BI Team và Data Science Team; bảo đảm SLA thời gian làm mới dữ liệu (Data Freshness SLA).
- Giao tiếp ngang: Phối hợp cùng SRE / Cloud Platform Team để tối ưu kích thước máy chủ, phân bổ node tính toán và kiểm soát ngân sách lưu trữ đám mây.
3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc lõi
- Kiến trúc Lakehouse: Apache Iceberg, Delta Lake, Apache Hudi kết hợp Object Storage (S3 / GCS / MinIO).
- Streaming Engine: Apache Kafka, Apache Flink (Streaming stateful processing), Spark Structured Streaming.
- Transformation &amp; Orchestration: dbt (data build tool), Apache Airflow, Dagster, PySpark.
- Query Engine &amp; Storage: ClickHouse (Real-time OLAP), Trino/Presto (Distributed SQL Query Engine), Snowflake, BigQuery.
4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành
- Vấn nạn "Small Files Problem" trong Data Lake:
- Vấn đề: Việc nạp dữ liệu liên tục từ các luồng streaming sinh ra hàng triệu file Parquet kích thước chỉ vài chục KB trên S3/HDFS, làm tê liệt Metadata NameNode và khiến các câu truy vấn SELECT bị nghẽn I/O nghiêm trọng.
- Bản chất kỹ thuật: Chi phí overhead mở/đóng file và đọc metadata lớn hơn thời gian đọc dữ liệu thực tế.
- Giải pháp: Tích hợp cơ chế tự động dọn dẹp và nén file (Compaction / Bin-packing) định kỳ bằng Apache Iceberg Maintenance Actions, tối ưu hóa kích thước file ở mức lý tưởng (128MB - 512MB).
- Xử lý dữ liệu đến trễ (Late-arriving Data) &amp; Tính chính xác một lần (Exactly-Once):
- Vấn đề: Sự cố mạng thiết bị di động khiến log giao dịch xuất hiện muộn hơn cửa sổ tính toán (Windowing) hàng giờ đồng hồ.
- Giải pháp: Thiết lập cơ chế Watermarking trong Flink hoặc Spark Streaming để cho phép chấp nhận độ trễ hợp lý; áp dụng cơ chế Checkpointing và Idempotent Sink để bảo đảm ngữ nghĩa Exactly-Once.
5. Tương tác chuyên môn &amp; Phản biện kỹ thuật
- Tranh luận kiến trúc: Lambda vs. Kappa vs. Lakehouse Unified:
- Bối cảnh: Doanh nghiệp muốn duy trì 2 luồng xử lý riêng biệt: một luồng Batch chạy Spark ban đêm, một luồng Streaming chạy Flink ban ngày để cập nhật dashboard.
- Phản biện: Chỉ ra sự lãng phí tài nguyên và rủi ro sai lệch logic (Logic Drift) khi phải viết code bằng 2 ngôn ngữ/framework khác nhau cho cùng một nghiệp vụ. Đề xuất quy hoạch về mô hình Lakehouse hợp nhất sử dụng Apache
26. Flink/Spark ghi trực tiếp vào Apache Iceberg, cho phép truy vấn trực tiếp dữ liệu cận thời gian thực (Near Real-time) trên cùng một bảng dữ liệu duy nhất.
6. Môi trường tác nghiệp &amp; Công cụ thực tế
- Hạ tầng làm việc: Hệ thống điều phối luồng Airflow UI, Kubernetes dashboard theo dõi các task Spark trên EKS, giao diện quản lý cụm Kafka (AKHQ / Kafka UI).
- Bộ công cụ chẩn đoán: Terminal chạy lệnh Linux CLI, theo dõi tiến trình I/O đĩa (iostat, iotop), truy vấn trực tiếp kế hoạch thực thi SQL (EXPLAIN ANALYZE) trên Trino Console.