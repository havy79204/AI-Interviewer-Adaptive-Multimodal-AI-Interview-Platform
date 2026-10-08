## [TÀI LIỆU 01] PHỎNG VẤN SENIOR DEVOPS / SRE (FINTECH &amp; HIGH LOAD)

1. Định vị chức danh &amp; Ngành nghề cốt lõi
- Vị trí: Senior DevOps Engineer / Site Reliability Engineer (SRE).
- Cấp bậc: Senior / Lead IC (Individual Contributor).
- Domain tiêu biểu: Fintech, Ngân hàng số, Cổng thanh toán trực tuyến, Crypto Exchange, Sàn TMĐT quy mô cao điểm.
- Mục tiêu then chốt trong buổi phỏng vấn: Kiểm chứng tư duy thiết kế hệ thống chịu lỗi (Fault Tolerance), kinh nghiệm "dập lửa" sự cố thực chiến (Zero-Downtime), tư duy tự động hóa (IaC/GitOps) và kỷ luật vận hành chuẩn bảo mật PCI-DSS.
2. Hệ sinh thái vai trò &amp; Hội đồng phỏng vấn
- Người phỏng vấn chính: Head of Infrastructure, Principal SRE, CTO/VP of Engineering.
- Giao diện làm việc thực tế: Phối hợp chặt chẽ với Backend Lead (tối ưu hóa kết nối DB, API latency), Security Lead (vá lỗ hổng container, quản trị khóa Vault), QA Lead (môi trường staging tự động) và Financial Controller (FinOps/ngân sách cloud).
3. Công nghệ xu hướng &amp; Khái niệm bắt buộc
- Kubernetes Nâng cao: eBPF (Cilium CNI), KEDA (Event-driven Autoscaling), Service Mesh (Istio/Linkerd), Gateway API.
- GitOps &amp; Pipeline: ArgoCD, Argo Rollouts (Canary/Blue-Green), Crossplane (thay thế hoặc bổ trợ Terraform).
- Observability 2.0: OpenTelemetry standard, Distributed Tracing (Jaeger/Tempo), Thanos/Cortex cho Prometheus quy mô lớn.
- Bảo mật hạ tầng: Secret Management (Vault Dynamic Secrets), Sigstore/Cosign (Container Image Signing), Kyverno/OPA Gatekeeper.
4. Kịch bản phỏng vấn kỹ thuật &amp; Tình huống "bắt bài"
- Câu hỏi kiến trúc: "Hệ thống Core Banking của chúng tôi chuẩn bị chạy chiến dịch Flash Sale với tải dự kiến tăng đột biến gấp 15 lần (từ 3,000 TPS lên 45,000 TPS) trong 10 phút. Bạn sẽ thiết lập chiến lược Auto-scaling và Resilience ở những tầng nào?"
- Kỳ vọng: Không chỉ trả lời đơn giản là "bật HPA". Cần nhắc đến: Pre-warming cụm máy chủ node EC2/GCE, Karpenter thay thế Cluster Autoscaler, kết nối DB Connection Pooling (PgBouncer/RDS Proxy), cơ chế Rate Limiting tại Ingress/WAF, và kỹ thuật Circuit Breaker/Graceful Degradation.
- Câu hỏi bẫy (Gotcha): "Một Pod trên Kubernetes bị crash liên tục với lỗi OOMKilled (Exit Code 137). Bạn tăng Memory Limit của Pod lên gấp đôi nhưng chỉ sau 20 phút nó lại tiếp tục OOM. Bạn xử lý thế nào thay vì tiếp tục tăng RAM?"
- Kỳ vọng: Nhận diện ngay vấn đề Rò rỉ bộ nhớ (Memory Leak) từ mã nguồn ứng dụng hoặc rò rỉ kết nối. Các bước thực hiện: Trích xuất Heap Dump trước khi Pod chết, sử dụng công cụ profiling (như pprof cho Go, VisualVM/JFR cho Java), kiểm tra cấu hình JVM heap size (-XX:MaxRAMPercentage) không vượt quá cgroup limit của Pod.
- Tình huống văn hóa (Culture &amp; Ownership): "Nếu bạn vô tình chạy một script Terraform và làm xóa mất một Database Replica trên Production trong giờ hành chính, 3 hành động đầu tiên bạn làm trong 5 phút tiếp theo là gì?"
- Kỳ vọng: Tính minh bạch và bình tĩnh: (1) Báo ngay lên kênh Incident nội bộ để chặn việc traffic đọc bị điều hướng vào node lỗi; (2) Thực hiện phương án phục hồi hoặc chuyển hướng traffic (Failover sang standby/read replica khác); (3) Sau khi ổn định, chủ động viết Blameless Post-mortem và bổ sung cờ prevent\_destroy trong Terraform state.
5. Sự cố phòng phỏng vấn &amp; Cách làm chủ không gian
- Môi trường Online:
- Sự cố: Mạng lag khi ứng viên đang chia sẻ màn hình kiến trúc hệ thống hoặc terminal.
- Xử lý: Đề xuất tắt camera cá nhân để nhường băng thông cho âm thanh và màn hình chia sẻ; chuẩn bị sẵn link GitHub Gist hoặc sơ đồ kiến trúc trên Miro/Excalidraw gửi trực tiếp vào ô chat để phỏng vấn viên tự mở.
- Môi trường Onsite (Whiteboard &amp; Vật dụng):
- Bảng trắng &amp; Bút dạ: Đừng vẽ ngay một đống hình hộp chữ nhật vô nghĩa. Hãy chia bảng thành 3 khu vực rõ ràng: (1) Trái: Ràng buộc &amp; Giả định hệ thống (Constraints, QPS, Latency SLA); (2) Giữa: Sơ đồ luồng dữ liệu &amp; Thành phần (Data Flow &amp; Architecture); (3) Phải: Chiến lược Chống lỗi &amp; Dự phòng (Edge Cases &amp; Fallbacks).
- Cốc nước trên bàn: Uống một ngụm nước ấm nhỏ trước khi trả lời câu hỏi hóc búa để có 5 giây định thần, điều chỉnh nhịp thở, tránh phát biểu vội vã.