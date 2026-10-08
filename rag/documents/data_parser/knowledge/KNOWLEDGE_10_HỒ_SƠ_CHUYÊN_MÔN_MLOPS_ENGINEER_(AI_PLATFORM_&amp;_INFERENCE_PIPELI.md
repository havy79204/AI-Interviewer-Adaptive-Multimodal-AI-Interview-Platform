## [TÀI LIỆU 10] HỒ SƠ CHUYÊN MÔN: MLOPS ENGINEER (AI PLATFORM &amp; INFERENCE PIPELINES)

## 1. Phạm vi vai trò &amp; Hệ quy chiếu ngành

- Vị trí cốt lõi: Machine Learning Operations (MLOps) Engineer / AI Platform Engineer.
- Domain ứng dụng: Autonomous Driving, Video/Audio Streaming Analytics, Nền tảng FinTech chống gian lận, Nền tảng phục vụ LLM quy mô công nghiệp.
- Mục tiêu then chốt của vị trí: Tự động hóa toàn bộ vòng đời của mô hình AI từ khâu đóng gói mã nguồn, kiểm thử hiệu năng, triển khai suy luận phân tán đến giám sát lệch dữ liệu; đảm bảo tính khả chuyển, khả năng tái lập (Reproducibility) và độ ổn định chuẩn hạ tầng production.

## 2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc

- Thượng nguồn: Tiếp nhận các trọng số mô hình đã hoàn thành thử nghiệm từ Data Scientist / AI Engineer; chuẩn hóa các dependency phức tạp của Python/CUDA.
- Hạ nguồn: Cung cấp cụm microservices inference sẵn sàng mở rộng cho Software Backend Engineer; chịu trách nhiệm duy trì SLA 99.9% cho các AI APIs.
- Giao tiếp ngang: Phối hợp với Cloud FinOps để cắt giảm chi phí GPU nhàn rỗi và làm việc với SecOps để quét mã độc trong các tệp nhị phân trọng số (Pickle scanning).

## 3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc lõi

- Serving &amp; Inference Engines: Triton Inference Server (hỗ trợ đa backend: PyTorch, ONNX, TensorRT), vLLM, TF-Serving, TorchServe.
- Pipeline Orchestration: Kubeflow Pipelines, Airflow, Prefect, GitHub Actions / GitLab CI for ML.
- Model Registry &amp; Tracking: MLflow, DVC (Data Version Control), Weights &amp; Biases Enterprise.
- Hạ tầng Kubernetes &amp; Phần cứng: NVIDIA GPU Operator, KEDA (Custom Metrics Autoscaling), MIG (Multi-Instance GPU), Karpenter GPU provisioning.

## 4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành

- Hiện tượng GPU Lãng phí tài nguyên (GPU Under-utilization):
- Vấn đề: Doanh nghiệp thuê 8 card NVIDIA A100 với giá hàng chục nghìn USD mỗi tháng nhưng mức độ sử dụng tính toán (GPU Compute Utilization) trung bình chỉ đạt 15-20%.
- Bản chất kỹ thuật: Quá trình suy luận bị nghẽn ở bước CPU tiền xử lý dữ liệu (Pre-processing), mạng I/O tải dữ liệu chậm, hoặc kích thước batch size quá nhỏ không tận dụng được sức mạnh tính toán song song của Tensor Cores.
- Giải pháp: Tận dụng kỹ thuật MIG (Multi-Instance GPU) để chia 1 card A100 thành 7 phân vùng GPU độc lập cho các tác vụ nhỏ; cấu hình Dynamic Batching trên Triton Server để tự động gom các request lẻ trong khoảng thời gian 5ms thành một batch lớn trước khi đẩy vào VRAM.
- Quản lý rủi ro bảo mật tệp mô hình (Arbitrary Code Execution via Pickle):
- Vấn đề: Tệp checkpoint mô hình Python (.pkl, .bin) có thể bị kẻ tấn công chèn mã khai thác thực thi từ xa (RCE) ngay khi gọi hàm torch.load().
- Giải pháp: Chuẩn hóa quy trình chuyển đổi toàn bộ mô hình sang định dạng SafeTensors hoặc ONNX trong pipeline CI/CD trước khi đưa vào Model Registry; áp dụng công cụ quét bảo mật Fickling/Picklescan tự động.
5. Tương tác chuyên môn &amp; Phản biện kỹ thuật
- Phản biện quy trình chuyển giao giữa Data Science và Vận hành:
- Tình huống: Data Scientist gửi cho bạn một tệp Jupyter Notebook dài 2,000 dòng kèm theo một file requirements.txt xung đột phiên bản CUDA và yêu cầu triển khai lên Production vào chiều cùng ngày.
- Chuẩn mực xử lý: Thiết lập tiêu chuẩn "Model as Code": Từ chối tiếp nhận notebook thủ công; yêu cầu mọi mô hình bàn giao phải tuân theo cấu trúc chuẩn (Model Artifact + Config + Input/Output Signature + Unit Test kiểm tra độ trễ); hỗ trợ thiết lập template Cookiecutter ML project để Data Scientist tự động đóng gói qua pipeline chuẩn.
6. Môi trường tác nghiệp &amp; Công cụ thực tế
- Hạ tầng làm việc: Bảng điều khiển Kubeflow UI theo dõi pipeline DAG, terminal theo dõi thông số card qua watch -n 1 nvidia-smi và nvtop.
- Môi trường giám sát: Dashboard Grafana hiển thị đồng thời 4 chỉ số vàng của hệ thống AI: Độ trễ (Inference Latency), Lưu lượng (Request Throughput), Tỷ lệ lỗi (Error Rate) và Mức độ bão hòa VRAM (GPU Saturation).